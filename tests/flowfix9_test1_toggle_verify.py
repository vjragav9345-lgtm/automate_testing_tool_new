"""FIX 1 (reliable post-action verification) - reproduces the exact real
bug from session_20260925_103118.json step 10 against a local fixture
(tests/fixtures/flowfix9_radio_race.html): a native <input type="radio">
wrapped in a <label>, inside a list the app fully re-renders ~400ms after
the click (matching the recorded navigate's own delay_before_ms=385)
before the URL/DOM actually reflect the new selection.

Before FIX 1: verification read state straight off `el` (the label
act_target, which never carries checked/aria-checked at all) with zero
settle time - guaranteed false failure. After FIX 1: settle + re-resolve
state_target fresh + poll up to 3s, accepting state-match OR the recorded
URL change - must PASS.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from phase4_test_helpers import run_test_case, step_lp  # noqa: E402
from phase4_fixture_server import FixtureServer  # noqa: E402


def build_test_case(base_url):
    act_lp = step_lp(
        text="20% and above", element_text="20% and above",
        css_path="ul#discountList > li:nth-of-type(2) > label",
        xpath="//label[normalize-space(text())='20% and above']",
        tag="label",
    )
    state_lp = step_lp(
        text="20% and above", element_text="20.0 TO 100.0",
        css_path="ul#discountList > li:nth-of-type(2) > label > input",
        xpath="//label[normalize-space(text())='20% and above']/input",
        tag="input", role="radio",
        attributes={"type": "radio", "name": "discount-product"},
    )
    state_lp["name"] = "discount-product"

    initial_nav_step = {
        "action_type": "navigate",
        "value": None,
        "locator_profile": {},
        "page_url": base_url,
    }
    check_step = {
        "action_type": "check",
        "value": None,
        "locator_profile": act_lp,
        "act_target": act_lp,
        "state_target": {"locator_profile": state_lp, "checked": True},
        "expected_state": True,
        "expect": {"type": "toggle", "final_checked": True},
        "bounding_box": {},
        "page_url": base_url,
        "dom_context": {
            "state_target_html_chain": [
                '<input type="radio" class="discount-input" name="discount-product" value="20.0 TO 100.0">',
            ],
        },
    }
    navigate_step = {
        "action_type": "navigate",
        "value": None,
        "locator_profile": {},
        "page_url": base_url + "?rf=Discount+Range%3A20.0+TO+100.0",
    }
    return {
        "name": "flowfix9_toggle_verify",
        "start_url": base_url,
        "actions": [initial_nav_step, check_step, navigate_step],
    }


def main():
    with FixtureServer() as srv:
        base_url = srv.url("flowfix9_radio_race.html")
        test_case = build_test_case(base_url)
        result, captured = run_test_case(test_case, "flowfix9_toggle_verify", headless=True)

    steps = result.get("steps", [])
    print("=== RESULT ===")
    for s in steps:
        print(s.get("index"), s.get("action_type"), s.get("success"), s.get("error"))

    check_result = next((s for s in steps if s.get("action_type") == "check"), None)
    assert check_result is not None, "no check step in result"
    assert check_result.get("success") is True, f"expected success=True, got: {check_result}"
    assert "[toggle-verify]" in captured, "expected the new toggle-verify log line"
    print("\nPASS: FIX 1 correctly verified the delayed radio toggle instead of false-failing")


if __name__ == "__main__":
    main()
