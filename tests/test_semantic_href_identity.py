"""Regression tests for links with stable destinations and changing tracking data."""
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import ModuleType
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from unittest.mock import patch

from generator.script_generator import generate_script


class _Candidate:
    def evaluate(self, *_args, **_kwargs):
        return {"kindVeto": False, "selfExact": False, "state": "none"}


class SemanticHrefIdentityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix="afqa-href-identity-")
        recording = {
            "name": "semantic_href_identity",
            "start_url": "https://shop.test/",
            "actions": [{
                "action_type": "click",
                "page_url": "https://shop.test/",
                "value": None,
                "locator_profile": {
                    "tag": "a",
                    "accessible_name": "Laptops",
                    "aria_label": "Laptops",
                    "text": "Laptops",
                    "href": ("/s/?_encoding=UTF8&k=laptops&pd_rd_w=old&"
                             "content-id=generated-value&pf_rd_r=OLDTOKEN"),
                    "attributes": {"aria-label": "Laptops"},
                },
                "bounding_box": {"x": 100, "y": 100, "width": 80, "height": 30},
            }],
        }
        script = generate_script(recording, out_name="semantic_href_identity.py", output_dir=Path(cls.temp.name))
        playwright = ModuleType("playwright")
        sync_api = ModuleType("playwright.sync_api")
        sync_api.sync_playwright = lambda: None
        playwright.sync_api = sync_api
        prior_playwright = sys.modules.get("playwright")
        prior_sync_api = sys.modules.get("playwright.sync_api")
        sys.modules.setdefault("playwright", playwright)
        sys.modules.setdefault("playwright.sync_api", sync_api)
        spec = importlib.util.spec_from_file_location("semantic_href_identity_generated", script)
        cls.mod = importlib.util.module_from_spec(spec)
        try:
            spec.loader.exec_module(cls.mod)
        finally:
            if prior_playwright is None:
                sys.modules.pop("playwright", None)
            else:
                sys.modules["playwright"] = prior_playwright
            if prior_sync_api is None:
                sys.modules.pop("playwright.sync_api", None)
            else:
                sys.modules["playwright.sync_api"] = prior_sync_api
        cls.lp = recording["actions"][0]["locator_profile"]
        cls.latest_recording = json.loads(
            (Path(__file__).resolve().parents[1] / "storage" / "recordings" /
             "session_20261007_204255.json").read_text(encoding="utf-8")
        )

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_same_route_and_search_intent_ignore_changed_tracking_values(self):
        live = {
            "tag": "a",
            "role": None,
            "href": ("/s/?_encoding=UTF8&k=laptops&pd_rd_w=new&"
                     "content-id=generated-value&pf_rd_r=NEWTOKEN"),
            "parts": ["Laptops Laptops Laptops Laptops"],
        }
        self.assertEqual(self.mod._identity_compare(self.lp, live), "match")

    def test_different_search_intent_or_route_remains_a_mismatch(self):
        wrong_query = {
            "tag": "a", "role": None, "href": "/s/?k=desktops",
            "parts": ["Laptops"],
        }
        wrong_path = {
            "tag": "a", "role": None, "href": "/cart?k=laptops",
            "parts": ["Laptops"],
        }
        self.assertEqual(self.mod._identity_compare(self.lp, wrong_query), "mismatch")
        self.assertEqual(self.mod._identity_compare(self.lp, wrong_path), "mismatch")

    def test_encoded_wrapper_matches_same_inner_product_with_fresh_tracking_values(self):
        recorded = self.latest_recording["actions"][6]["locator_profile"]
        href = self._live_wrapped_href(recorded["href"])
        live = {
            "tag": "a", "role": None,
            "href": href,
            "parts": ["Sponsored Ad - Dockers Boys' Long Sleeve Poplin Button Down Shirt"],
        }
        self.assertEqual(self.mod._identity_compare(recorded, live), "match")

    def test_encoded_wrapper_for_another_product_is_rejected(self):
        recorded = self.latest_recording["actions"][6]["locator_profile"]
        href = self._live_wrapped_href(recorded["href"], other_product=True)
        live = {
            "tag": "a", "role": None,
            "href": href,
            "parts": ["Sponsored Ad - Dockers Boys' Long Sleeve Poplin Button Down Shirt"],
        }
        self.assertEqual(self.mod._identity_compare(recorded, live), "mismatch")

    @staticmethod
    def _live_wrapped_href(recorded_href, other_product=False):
        outer = urlsplit(recorded_href)
        outer_pairs = parse_qsl(outer.query, keep_blank_values=True)
        updated = []
        for key, value in outer_pairs:
            if key == "spc":
                value = "fresh-request-token-987654321"
            elif key == "url":
                inner = urlsplit(value)
                inner_path = inner.path.replace("B0GRJL38R3", "B0OTHER123") if other_product else inner.path
                inner_pairs = parse_qsl(inner.query, keep_blank_values=True)
                inner_pairs = [(k, "fresh-request-id-123456789" if k == "pd_rd_r" else v)
                               for k, v in inner_pairs]
                value = urlunsplit((inner.scheme, inner.netloc, inner_path,
                                    urlencode(inner_pairs, doseq=True), inner.fragment))
            updated.append((key, value))
        return urlunsplit((outer.scheme, outer.netloc, outer.path,
                           urlencode(updated, doseq=True), outer.fragment))

    def test_recording_kept_full_clicked_image_link_and_product_context(self):
        action = self.latest_recording["actions"][6]
        lp = action["locator_profile"]
        self.assertEqual(action["action_type"], "click")
        self.assertEqual(lp["tag"], "a")
        self.assertEqual(lp["content_hint"], "image")
        self.assertIn("B0GRJL38R3", lp["href"])
        self.assertIn("Dockers Boys' Long Sleeve Poplin Button Down Shirt", lp["inner_label"])
        self.assertEqual(lp["item_context"]["text"], "Dockers Boys' Long Sleeve Poplin Button Down Shirt")
        self.assertIn("<a ", action["dom_context"]["act_target_html_chain"][0])

    def test_final_candidate_gate_accepts_verified_semantic_destination(self):
        candidate = _Candidate()
        live = {
            "tag": "a", "role": None,
            "href": ("/s/?_encoding=UTF8&k=laptops&pd_rd_w=new&"
                     "content-id=generated-value&pf_rd_r=NEWTOKEN"),
            "parts": ["Laptops Laptops Laptops Laptops"],
        }
        page = object()
        step = {"action_type": "click", "locator_profile": self.lp, "bounding_box": {}}
        with patch.object(self.mod, "_live_identity_of", return_value=live), \
             patch.object(self.mod, "_pin_candidate", return_value=candidate):
            # The same final gate is used by every locator tier in replay.
            selected, reason = self.mod._final_decision(page, candidate, self.lp, step, "identity")
        self.assertIs(selected, candidate, reason)

    def test_final_candidate_gate_accepts_same_nested_product_identity(self):
        recorded = self.latest_recording["actions"][6]["locator_profile"]
        candidate = _Candidate()
        live = {
            "tag": "a", "role": None,
            "href": self._live_wrapped_href(recorded["href"]),
            "parts": ["Sponsored Ad - Dockers Boys' Long Sleeve Poplin Button Down Shirt"],
        }
        with patch.object(self.mod, "_live_identity_of", return_value=live), \
             patch.object(self.mod, "_pin_candidate", return_value=candidate):
            selected, reason = self.mod._final_decision(
                object(), candidate, recorded,
                {"action_type": "click", "locator_profile": recorded, "bounding_box": {}},
                "identity",
            )
        self.assertIs(selected, candidate, reason)


if __name__ == "__main__":
    unittest.main(verbosity=2)
