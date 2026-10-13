"""Focused offline regression checks for replay warning classification."""
import unittest
import sys
import json
import importlib.util
import tempfile
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from generator.script_generator import generate_script
from validation import report_generator


class _Context:
    pages = [object()]


class _Page:
    url = "https://example.test/dashboard"
    context = _Context()

    def __init__(self, live):
        self.live = live

    def evaluate(self, _script):
        return self.live


class WarningClassificationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._temp = tempfile.TemporaryDirectory(prefix="autoflow-warning-test-")
        recording = json.loads((Path(__file__).resolve().parent.parent /
                                "storage/recordings/session_20261007_111714.json").read_text(encoding="utf-8"))
        generated = generate_script(recording, out_name="warning_test_script.py",
                                    output_dir=Path(cls._temp.name))
        spec = importlib.util.spec_from_file_location("warning_test_script", generated)
        cls.replay = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.replay)

    @classmethod
    def tearDownClass(cls):
        cls._temp.cleanup()

    def setUp(self):
        self.replay._STEP_WARNINGS.clear()
        self.replay._STEP_DETAILS.clear()

    def test_statuses_keep_functional_success_distinct(self):
        self.assertEqual(report_generator._step_outcome({"success": True}), "pass")
        self.assertEqual(report_generator._step_outcome({"success": True, "warning": "unverified fallback"}), "warning")
        self.assertEqual(report_generator._step_outcome({"success": False, "error": "assertion failed"}), "fail")

    def test_confirmed_submit_field_clear_is_not_an_unexpected_side_effect(self):
        rec = {
            "url_path_before": self._page.url,
            "url_path_after": self._page.url,
            "fields_changed": [],
            "submit": {"fields_before": 1, "field_cleared": True, "content_added": True},
        }
        step = {"action_type": "click", "name": "send", "page_url": self._page.url, "post_click": rec}
        live = {"url": "https://example.test/dashboard", "focus": None,
                "fields_changed": [{"parts": [], "tag": "textarea", "type": None}], "fields_ignored": []}
        with patch.object(self.replay, "_wait_for_settle"), patch.object(self.replay, "_settle_click_navigation", return_value=self._page.url):
            result = self.replay._compare_post_click(_Page(live), step, True, 1)
        self.assertIsNone(result)
        self.assertFalse(self.replay._STEP_WARNINGS)
        self.assertTrue(any("field changed as part of the submission" in x for x in self.replay._STEP_DETAILS))

    def test_unrelated_changed_field_still_warns(self):
        rec = {"url_path_before": self._page.url, "url_path_after": self._page.url,
               "fields_changed": [], "submit": {"fields_before": 1, "field_cleared": True, "content_added": True}}
        step = {"action_type": "click", "name": "send", "page_url": self._page.url, "post_click": rec}
        live = {"url": "https://example.test/dashboard", "focus": None,
                "fields_changed": [{"parts": ["Account name"], "tag": "input", "type": "text"},
                                   {"parts": [], "tag": "textarea", "type": None}], "fields_ignored": []}
        with patch.object(self.replay, "_wait_for_settle"), patch.object(self.replay, "_settle_click_navigation", return_value=self._page.url):
            self.replay._compare_post_click(_Page(live), step, True, 1)
        self.assertTrue(any("also changed" in x for x in self.replay._STEP_WARNINGS))

    def test_dynamic_reply_difference_is_details_not_warning(self):
        step = {"reply_text": "recorded response"}
        with patch.object(self.replay, "_chat_new_lines", return_value=["different replay response"]):
            self.replay._chat_compare_reply(object(), step)
        self.assertFalse(self.replay._STEP_WARNINGS)
        self.assertTrue(any("differed from the replay response" in x for x in self.replay._STEP_DETAILS))

    def test_slow_success_diagnostic_does_not_change_status(self):
        detail = "DIAGNOSTIC - this step took more than 10s (found by 'identity')."
        self.assertEqual(report_generator._step_outcome({"success": True, "technical": detail}), "pass")

    def test_independently_confirmed_position_fallback_can_be_clean_pass(self):
        step = {"success": True, "strategy_used": "position_fallback",
                "technical": "recorded control name and item context independently confirmed"}
        self.assertEqual(report_generator._step_outcome(step), "pass")

    def test_no_field_change_produces_no_side_effect_warning(self):
        rec = {"url_path_before": self._page.url, "url_path_after": self._page.url,
               "fields_changed": [], "submit": {"fields_before": 1, "field_cleared": False, "content_added": False}}
        step = {"action_type": "click", "name": "control", "page_url": self._page.url, "post_click": rec}
        live = {"url": "https://example.test/dashboard", "focus": None,
                "fields_changed": [], "fields_ignored": []}
        with patch.object(self.replay, "_wait_for_settle"), patch.object(self.replay, "_settle_click_navigation", return_value=self._page.url):
            self.assertIsNone(self.replay._compare_post_click(_Page(live), step, True, 1))
        self.assertFalse(self.replay._STEP_WARNINGS)

    def test_unverified_fallback_remains_warning_and_explicit_assertion_failure_stays_fail(self):
        self.assertEqual(report_generator._step_outcome({"success": True, "strategy_used": "position_fallback",
                                                        "warning": "target not independently confirmed"}), "warning")
        self.assertEqual(report_generator._step_outcome({"success": False, "action_type": "validate_text",
                                                        "error": "expected text was not found"}), "fail")

    def test_recoverable_warning_does_not_change_later_step_outcome(self):
        steps = [
            {"success": True, "warning": "unverified fallback"},
            {"success": True},
        ]
        outcomes = [report_generator._step_outcome(x) for x in steps]
        self.assertEqual(outcomes, ["warning", "pass"])
        self.assertEqual(report_generator.honest_summary(
            [{"index": 1, **steps[0]}, {"index": 2, **steps[1]}], 2
        ), "1 step matched the recording, 1 step passed with a warning (see step 1).")

    @property
    def _page(self):
        return _Page({"url": "https://example.test/dashboard", "focus": None,
                      "fields_changed": [], "fields_ignored": []})


if __name__ == "__main__":
    unittest.main()
