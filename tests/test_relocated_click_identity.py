"""Focused checks for semantic click identity when a link's rank path changes."""
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import ModuleType
from unittest.mock import patch

from generator.script_generator import generate_script


class _Element:
    def __init__(self, box):
        self.box = box

    def bounding_box(self):
        return self.box


class _Page:
    def evaluate(self, *_args, **_kwargs):
        return [0, 700]


class RelocatedClickIdentityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix="afqa-relocated-click-")
        root = Path(__file__).resolve().parents[1]
        cls.recording = json.loads(
            (root / "storage" / "recordings" / "session_20261007_210841.json")
            .read_text(encoding="utf-8")
        )
        script = generate_script(
            cls.recording, out_name="relocated_click_identity.py", output_dir=Path(cls.temp.name)
        )
        playwright = ModuleType("playwright")
        sync_api = ModuleType("playwright.sync_api")
        sync_api.sync_playwright = lambda: None
        playwright.sync_api = sync_api
        prior_playwright = sys.modules.get("playwright")
        prior_sync_api = sys.modules.get("playwright.sync_api")
        sys.modules.setdefault("playwright", playwright)
        sys.modules.setdefault("playwright.sync_api", sync_api)
        spec = importlib.util.spec_from_file_location("relocated_click_identity_generated", script)
        cls.replay = importlib.util.module_from_spec(spec)
        try:
            spec.loader.exec_module(cls.replay)
        finally:
            if prior_playwright is None:
                sys.modules.pop("playwright", None)
            else:
                sys.modules["playwright"] = prior_playwright
            if prior_sync_api is None:
                sys.modules.pop("playwright.sync_api", None)
            else:
                sys.modules["playwright.sync_api"] = prior_sync_api
        cls.action = cls.recording["actions"][11]
        cls.profile = cls.action["locator_profile"]

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_same_product_with_changed_rank_path_remains_same_identity(self):
        live = {
            "tag": "a",
            "role": None,
            "href": self.profile["href"].replace("ref=sr_1_8", "ref=sr_1_2"),
            "parts": [self.profile["inner_label"]],
        }
        self.assertEqual(self.replay._identity_compare(self.profile, live), "match")

    def test_different_item_with_same_name_is_not_accepted(self):
        live = {
            "tag": "a",
            "role": None,
            "href": self.profile["href"].replace("B07XVY344Z", "B07DIFFERENT"),
            "parts": [self.profile["inner_label"]],
        }
        self.assertEqual(self.replay._identity_compare(self.profile, live), "mismatch")

    def test_click_identity_guard_accepts_same_item_after_position_change(self):
        live = {
            "tag": "a",
            "role": None,
            "href": self.profile["href"].replace("ref=sr_1_8", "ref=sr_1_2"),
            "parts": [self.profile["inner_label"]],
        }
        with patch.object(self.replay, "_live_identity_of", return_value=live):
            failed, reason = self.replay._warn_if_resolved_identity_mismatched(
                object(), self.profile, "click"
            )
        self.assertFalse(failed, reason)
        self.assertIsNone(reason)

    def test_relocation_warning_data_uses_current_element_geometry(self):
        self.replay._FINAL_DECISION_CONFIRMED[0] = True
        info = self.replay._verified_target_relocation(
            _Page(), _Element({"x": 521, "y": 239, "width": 225, "height": 225}), self.action
        )
        self.assertIsNotNone(info)
        self.assertEqual(info["recorded"], (1022.0, 133.60000610351562 + 604.7999877929688))
        self.assertEqual(info["current"], (521.0, 939.0))

    def test_unverified_candidate_does_not_receive_relocation_note(self):
        self.replay._FINAL_DECISION_CONFIRMED[0] = False
        info = self.replay._verified_target_relocation(
            _Page(), _Element({"x": 10, "y": 20, "width": 225, "height": 225}), self.action
        )
        self.assertIsNone(info)

    def test_successful_relocation_warning_reports_old_and_current_positions(self):
        info = {"recorded": (1022.0, 738.4), "current": (521.0, 939.0), "distance": 539.7}
        messages = []
        with patch.object(self.replay, "_add_step_warning", side_effect=messages.append):
            self.replay._warn_verified_target_relocation(info)
        self.assertEqual(len(messages), 1)
        self.assertIn("(1022, 738)", messages[0])
        self.assertIn("(521, 939)", messages[0])
        self.assertIn("same logical target was verified and clicked", messages[0])


if __name__ == "__main__":
    unittest.main(verbosity=2)
