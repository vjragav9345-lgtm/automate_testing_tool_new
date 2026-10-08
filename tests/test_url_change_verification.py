"""Focused URL destination and live-log regressions using generated replay code.

These tests exercise the same helpers embedded in replay runners without
contacting a live website or starting a browser.
"""
import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path
from types import ModuleType

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))
from generator.script_generator import generate_script  # noqa: E402


class _Page:
    def __init__(self, url):
        self.url = url

    def wait_for_url(self, *_args, **_kwargs):
        raise TimeoutError("destination did not arrive")

    def wait_for_timeout(self, _ms):
        pass


class URLChangeVerificationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._tmp = tempfile.TemporaryDirectory(prefix="autoflow_url_verify_")
        cls.input_url = "https://shop.test/"
        cls.recorded_url = (
            "https://shop.test/search/legacy?field-keywords=shirts&"
            "sprefix=shirts%2Caps%2C338&crid=2GUD0GKGKL81X"
        )
        cls.canonical_url = (
            "https://shop.test/search?k=shirts&crid=2GUD0GKGKL81X&"
            "sprefix=shirts%2Caps%2C338&ref=search"
        )
        cls.changed_url = (
            "https://shop.test/search?k=shirts&crid=Q42RSSP5CD6E&"
            "sprefix=shirts%2Caps%2C434&ref=search"
        )
        actions = [
            {"action_type": "navigate", "page_url": cls.input_url, "locator_profile": {}, "value": None},
            {"action_type": "fill", "page_url": cls.input_url, "value": "shirts", "value_source": "user",
             "locator_profile": {"tag": "input"}},
            {"action_type": "click", "page_type": "search", "page_url": cls.input_url, "value": None,
             "expected_url": cls.recorded_url,
             "expected_url_chain": [cls.recorded_url, cls.canonical_url],
             "post_click": {"url_path_before": cls.input_url, "url_path_after": "https://shop.test/search",
                            "navigated": True},
             "locator_profile": {"tag": "button"}},
        ]
        script = generate_script(
            {"name": "url_change_verification", "start_url": cls.input_url, "actions": actions},
            out_name="url_change_verification.py", output_dir=Path(cls._tmp.name),
        )

        # The tests call URL helpers only. Stub the runner's top-level browser
        # import so they remain runnable when this environment has no Playwright.
        playwright = ModuleType("playwright")
        sync_api = ModuleType("playwright.sync_api")
        sync_api.sync_playwright = lambda: None
        playwright.sync_api = sync_api
        prior_playwright = sys.modules.get("playwright")
        prior_sync_api = sys.modules.get("playwright.sync_api")
        sys.modules.setdefault("playwright", playwright)
        sys.modules.setdefault("playwright.sync_api", sync_api)

        spec = importlib.util.spec_from_file_location("url_change_verification_generated", script)
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

    @classmethod
    def tearDownClass(cls):
        cls._tmp.cleanup()

    def setUp(self):
        self.mod._USER_INPUT_TEXTS_CACHE[0] = None
        self.mod._URL_NOTES_SAID.clear()
        self.mod._STEP_DETAILS.clear()
        self.logs = []
        self.original_url_log = self.mod._url_note_log
        self.mod._url_note_log = lambda message, *args, **kwargs: self.logs.append(message)

    def tearDown(self):
        self.mod._url_note_log = self.original_url_log

    def _click_step(self):
        return self.mod.STEPS[2]

    def test_amazon_recorded_and_replayed_urls_are_accepted_with_info_log(self):
        recorded = (
            "https://www.amazon.com/s/ref=nb_sb_noss_1?url=search-alias%3Daps&"
            "field-keywords=shirts&crid=2GUD0GKGKL81X&sprefix=shirts%2Caps%2C338"
        )
        recorded_canonical = (
            "https://www.amazon.com/s?k=shirts&crid=2GUD0GKGKL81X&"
            "sprefix=shirts%2Caps%2C338&ref=nb_sb_noss_1"
        )
        replayed = (
            "https://www.amazon.com/s?k=shirts&crid=Q42RSSP5CD6E&"
            "sprefix=shirts%2Caps%2C434&ref=nb_sb_noss_1"
        )
        step = dict(self._click_step())
        step["expected_url"] = recorded
        step["expected_url_chain"] = [recorded, recorded_canonical]
        step["post_click"] = {
            "url_path_before": "https://www.amazon.com/",
            "url_path_after": "https://www.amazon.com/s",
            "navigated": True,
        }
        page = _Page(replayed)
        # The previous substring rule rejected this exact recorded route
        # variant because the derived sprefix contains "shirts" plus a
        # changing suffix. Keep that failure as the regression control.
        original_matcher = self.mod._is_user_input_value
        self.mod._is_user_input_value = lambda value, texts: (
            bool(self.mod._norm_user_text(value))
            and any(self.mod._norm_user_text(value) == text or text in self.mod._norm_user_text(value)
                    for text in texts)
        )
        self.mod._USER_INPUT_TEXTS_CACHE[0] = None
        try:
            self.assertEqual(self.mod._classify_url(page.url, recorded, step["expected_url_chain"]), "mismatch")
        finally:
            self.mod._is_user_input_value = original_matcher
            self.mod._USER_INPUT_TEXTS_CACHE[0] = None
        self.assertEqual(self.mod._classify_url(page.url, recorded, step["expected_url_chain"]), "query")

        failure = self.mod._compare_post_click(
            page, step, snapshot_ok=True, page_count_before=1, qa_url=None,
            url_at_start="https://www.amazon.com/", destination_only=True,
        )

        self.assertIsNone(failure)
        self.assertTrue(any(msg.startswith("[INFO] The URL changed") for msg in self.logs), self.logs)
        self.assertTrue(any("Recorded destination:" in d and page.url in d for d in self.mod._STEP_DETAILS))

    def test_generic_recorded_route_variant_is_accepted(self):
        step = self._click_step()
        self.assertNotEqual(self.mod._classify_url(self.canonical_url, step["expected_url"]), "match")
        self.assertNotEqual(
            self.mod._classify_url(self.canonical_url, step["expected_url"], step["expected_url_chain"]),
            "mismatch",
        )

    def test_query_parameter_order_and_tracking_changes_still_match(self):
        actual = "https://shop.test/search?utm_source=other&k=shirts&ref=other"
        target = "https://shop.test/search?ref=search&k=shirts&utm_source=original"
        self.assertEqual(self.mod._classify_url(actual, target), "match")

    def test_verified_same_route_query_reordering_is_logged(self):
        target = "https://shop.test/search?k=shirts&ref=search&utm_source=original"
        actual = "https://shop.test/search?utm_source=other&k=shirts&ref=other"
        step = dict(self._click_step(), expected_url=target, expected_url_chain=[])
        failure = self.mod._compare_post_click(
            _Page(actual), step, snapshot_ok=True, page_count_before=1, qa_url=None,
            url_at_start=self.input_url,
            destination_only=True,
        )
        self.assertIsNone(failure)
        self.assertTrue(any(msg.startswith("[INFO] The URL changed") for msg in self.logs), self.logs)

    def test_dynamic_session_value_changes_still_match(self):
        actual = "https://shop.test/search?k=shirts&session_id=Q42RSSP5CD6E"
        target = "https://shop.test/search?session_id=2GUD0GKGKL81X&k=shirts"
        self.assertEqual(self.mod._classify_url(actual, target), "match")

    def test_search_term_inside_derived_value_is_not_mistaken_for_user_input(self):
        self.assertFalse(self.mod._is_user_input_value("shirts,caps,434", {"shirts"}))
        self.assertTrue(self.mod._is_user_input_value("SHIRTS", {"shirts"}))

    def test_recorded_alternate_format_and_redirect_chain_are_verified(self):
        actual = "https://shop.test/search?k=shirts&ref=redirected"
        self.assertNotEqual(self.mod._classify_url(actual, self.recorded_url), "match")
        self.assertNotEqual(self.mod._classify_url(actual, self.recorded_url, [self.canonical_url]), "mismatch")

    def test_search_intent_change_is_rejected(self):
        actual = "https://shop.test/search?k=pants&crid=Q42RSSP5CD6E"
        self.assertEqual(self.mod._classify_url(actual, self.canonical_url), "mismatch")

    def test_unrelated_path_and_domain_are_rejected(self):
        self.assertEqual(self.mod._classify_url("https://shop.test/cart?k=shirts", self.canonical_url), "mismatch")
        self.assertEqual(self.mod._classify_url("https://other.test/search?k=shirts", self.canonical_url), "mismatch")

    def test_same_page_interaction_without_navigation_is_not_failed(self):
        step = {
            "page_url": self.input_url,
            "post_click": {"url_path_before": self.input_url, "url_path_after": self.input_url, "navigated": False},
            "locator_profile": {},
        }
        page = _Page(self.input_url)
        self.assertIsNone(self.mod._compare_post_click(
            page, step, snapshot_ok=True, page_count_before=1, qa_url=None,
            url_at_start=self.input_url, destination_only=True,
        ))

    def test_navigation_timeout_fails_and_is_explained(self):
        step = self._click_step()
        page = _Page(self.input_url)
        failure = self.mod._compare_post_click(
            page, step, snapshot_ok=True, page_count_before=1, qa_url=None,
            url_at_start=self.input_url, destination_only=True,
        )
        self.assertIn("did not change the way it did during recording", failure)
        self.assertTrue(any(msg.startswith("[FAILED] The expected navigation did not complete") for msg in self.logs), self.logs)

    def test_wrong_destination_fails_and_is_explained(self):
        step = self._click_step()
        page = _Page("https://shop.test/cart")
        failure = self.mod._compare_post_click(
            page, step, snapshot_ok=True, page_count_before=1, qa_url=None,
            url_at_start=self.input_url, destination_only=True,
        )
        self.assertIn("PAGE_MISMATCH", failure)
        self.assertTrue(any(msg.startswith("[FAILED] The URL changed") for msg in self.logs), self.logs)

    def test_exact_destination_is_still_accepted_without_change_note(self):
        step = self._click_step()
        failure = self.mod._compare_post_click(
            _Page(self.recorded_url), step, snapshot_ok=True, page_count_before=1, qa_url=None,
            url_at_start=self.input_url, destination_only=True,
        )
        self.assertIsNone(failure)
        self.assertFalse(any(msg.startswith("[INFO] The URL changed") for msg in self.logs), self.logs)

    def test_stable_destination_path_accepts_changed_rank_context(self):
        recorded = "https://shop.test/Item-Name/dp/ENTITY123/ref=sr_1_7?q=shirts&utm_source=old"
        replayed = "https://shop.test/Item-Name/dp/ENTITY123/ref=sr_1_15?q=shirts&utm_source=new"
        step = dict(self._click_step(), expected_url=recorded, expected_url_chain=[recorded])

        self.assertEqual(self.mod._classify_url(replayed, recorded), "match")
        failure = self.mod._compare_post_click(
            _Page(replayed), step, snapshot_ok=True, page_count_before=1, qa_url=None,
            url_at_start="https://shop.test/search?q=shirts", destination_only=True,
        )

        self.assertIsNone(failure)
        self.assertTrue(any("stable path identity" in msg for msg in self.logs), self.logs)

    def test_stable_destination_path_keeps_entity_identity_strict(self):
        recorded = "https://shop.test/Item-Name/dp/ENTITY123/ref=sr_1_7"
        other_entity = "https://shop.test/Item-Name/dp/ENTITY999/ref=sr_1_15"

        self.assertEqual(self.mod._classify_url(other_entity, recorded), "mismatch")

    def test_stable_destination_path_still_checks_recorded_search_intent(self):
        recorded = "https://shop.test/Item-Name/dp/ENTITY123/ref=sr_1_7?q=shirts"
        changed_search = "https://shop.test/Item-Name/dp/ENTITY123/ref=sr_1_15?q=pants"

        self.assertEqual(self.mod._classify_url(changed_search, recorded), "mismatch")

    def test_same_path_without_parameter_context_does_not_gain_path_wildcard(self):
        recorded = "https://shop.test/item/one"
        different = "https://shop.test/item/two"

        self.assertEqual(self.mod._classify_url(different, recorded), "mismatch")


if __name__ == "__main__":
    unittest.main()
