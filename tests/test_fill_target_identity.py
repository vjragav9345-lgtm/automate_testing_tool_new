"""Regression coverage for Fill targets whose recorded locator is reused."""
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from generator.script_generator import generate_script


ROOT = Path(__file__).resolve().parents[1]
RECORDING = ROOT / "storage" / "recordings" / "session_20261007_153501.json"


class _Candidate:
    def __init__(self, decision):
        self.decision = decision
        self.evaluations = 0

    def evaluate(self, _script, *_args, **_kwargs):
        self.evaluations += 1
        if self.evaluations == 1:
            return self.decision
        return True


class _Page:
    url = "https://example.test/product"

    def __init__(self, candidate):
        self.candidate = candidate

    def locator(self, _selector):
        return self.candidate


class FillTargetIdentityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix="afqa-fill-identity-")
        recording = json.loads(RECORDING.read_text(encoding="utf-8"))
        generated = generate_script(recording, out_name="fill_identity_regression.py", output_dir=Path(cls.temp.name))
        spec = importlib.util.spec_from_file_location("fill_identity_regression", generated)
        cls.replay = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.replay)
        cls.action = recording["actions"][30]

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_strong_name_locator_cannot_override_conflicting_fill_identity(self):
        lp = self.action["locator_profile"]
        step = {"action_type": "fill", "locator_profile": lp, "bounding_box": {}}
        candidate = _Candidate({
            "kindVeto": False,
            "selfExact": False,
            "state": "none",
            "liveNames": ["search for products, brands and more"],
            "liveKind": "field",
        })
        live = {"tag": "input", "role": None, "parts": ["search for products, brands and more"]}
        self.replay._FINAL_DECISION_CONFIRMED[0] = False
        with patch.object(self.replay, "_live_identity_of", return_value=live):
            selected, reason = self.replay._final_decision(_Page(candidate), candidate, lp, step, "name")
        self.assertIsNone(selected)
        self.assertIn("search for products", reason)
        self.assertIn("Enter pincode", reason)

    def test_current_equivalent_fill_field_still_passes_semantic_identity(self):
        lp = self.action["locator_profile"]
        step = {"action_type": "fill", "locator_profile": lp, "bounding_box": {}}
        candidate = _Candidate({
            "kindVeto": False,
            "selfExact": False,
            "state": "none",
            "liveNames": ["Enter pincode"],
            "liveKind": "field",
        })
        live = {"tag": "input", "role": None, "parts": ["Enter pincode"]}
        self.replay._FINAL_DECISION_CONFIRMED[0] = False
        with patch.object(self.replay, "_live_identity_of", return_value=live):
            selected, reason = self.replay._final_decision(_Page(candidate), candidate, lp, step, "name")
        self.assertIsNotNone(selected, reason)

    def test_recorded_step_31_selects_current_equivalent_not_disabled_same_name_input(self):
        try:
            from playwright.sync_api import sync_playwright
        except ImportError as exc:
            self.skipTest(f"Playwright is unavailable: {exc}")
        with sync_playwright() as playwright:
            try:
                browser = playwright.chromium.launch(headless=True)
            except Exception as exc:
                self.skipTest(f"Chromium could not be launched in this environment: {exc}")
            try:
                page = browser.new_page()
                page.set_content("""
                  <input type="text" name="pincode" placeholder="search for products, brands and more"
                         aria-label="search for products, brands and more" disabled>
                  <input type="text" name="delivery" placeholder="Enter pincode" aria-label="Enter pincode">
                  <button id="continue" type="button" onclick="document.body.dataset.continued='yes'">Continue</button>
                """)
                step = dict(self.replay.STEPS[30])
                strategy, found, success, error = self.replay._resolve_and_act_core(page, step)
                self.assertTrue(found, (strategy, error))
                self.assertTrue(success, (strategy, error))
                self.assertEqual(page.locator('input[name="delivery"]').input_value(), "6410259")
                self.assertEqual(
                    page.locator('input[name="pincode"]').get_attribute("placeholder"),
                    "search for products, brands and more",
                )
                self.assertEqual(page.locator('input[name="pincode"]').input_value(), "")
                followup = {
                    "action_type": "click",
                    "locator_profile": {
                        "id": "#continue", "tag": "button", "text": "Continue",
                        "element_text": "Continue", "accessible_name": "Continue",
                        "attributes": {"id": "continue", "type": "button"},
                    },
                    "bounding_box": {},
                }
                next_strategy, next_found, next_success, next_error = self.replay._resolve_and_act_core(page, followup)
                self.assertTrue(next_found, (next_strategy, next_error))
                self.assertTrue(next_success, (next_strategy, next_error))
                self.assertEqual(page.locator("body").get_attribute("data-continued"), "yes")
            finally:
                browser.close()


if __name__ == "__main__":
    unittest.main(verbosity=2)
