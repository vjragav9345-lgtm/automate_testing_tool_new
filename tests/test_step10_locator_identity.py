"""Focused regressions for accessible-name drift in recorded click targets."""
import importlib.util
import json
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from playwright.sync_api import sync_playwright

from generator.script_generator import generate_script


ROOT = Path(__file__).resolve().parents[1]
RECORDING = ROOT / "storage" / "recordings" / "session_20261007_142344.json"


class _FixtureHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(b"<html><head><title>locator fixture</title></head><body></body></html>")

    def log_message(self, *_args):
        pass


class Step10LocatorIdentityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix="afqa-step10-")
        cls.out = Path(cls.temp.name)
        with RECORDING.open(encoding="utf-8") as f:
            tc = json.load(f)
        cls.tc = tc
        script = generate_script(tc, out_name="step10_regression.py", output_dir=cls.out)
        spec = importlib.util.spec_from_file_location("step10_generated", script)
        cls.mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.mod)
        cls.lp = tc["actions"][9]["locator_profile"]
        cls.pw = sync_playwright().start()
        cls.browser = cls.pw.chromium.launch(headless=True)
        cls.page = cls.browser.new_page()
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), _FixtureHandler)
        cls.server_thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.server_thread.start()
        cls.fixture_url = f"http://127.0.0.1:{cls.server.server_port}/fwdgenzcollection"

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.pw.stop()
        cls.server.shutdown()
        cls.server.server_close()
        cls.server_thread.join(timeout=2)
        cls.temp.cleanup()

    def setUp(self):
        self.page.goto(self.fixture_url)
        self.page.set_content("<main></main>")

    def test_truncated_name_and_extra_accessible_details_resolve_by_recorded_href(self):
        self.page.set_content('''<main><a id="target" href="/sweatshirts/la-pajaro/46109301/buy">
          <span>NEW</span><h2>La Pajaro Printed Sweatshirt</h2>
          <span>Rs. 475 Rs. 999 (52% OFF)</span></a></main>''')
        loc = self.mod._find_by_href(self.page, self.lp)
        self.assertIsNotNone(loc)
        # This is the stage the original replay rejected before reaching the
        # verifier: the live name differs, while the recorded link identity
        # proves it is the same target.
        chosen, reason = self.mod._final_decision(
            self.page, loc, self.lp, {"action_type": "click", "locator_profile": self.lp}, "href"
        )
        self.assertIsNotNone(chosen, reason)
        ok, reason = self.mod._verify_resolved_target(self.page, loc, self.lp, strategy="href")
        self.assertTrue(ok, reason)

    def test_similar_name_with_different_product_destination_is_rejected(self):
        self.page.set_content('''<main><a href="sweatshirts/la-pajaro/la-pajaro-men-printed-sweatshirt/46109302/buy">
          NEW La Pajaro Printed Sweatshirt Rs. 475Rs. 999(52% OFF)</a></main>''')
        candidate = self.page.locator("a").first
        chosen, reason = self.mod._final_decision(
            self.page, candidate, self.lp, {"action_type": "click", "locator_profile": self.lp}, "href"
        )
        self.assertIsNone(chosen)
        self.assertIn("name is", reason)

    def test_stale_candidate_is_rejected_by_validation(self):
        self.page.set_content('''<a id="target" href="sweatshirts/la-pajaro/la-pajaro-men-printed-sweatshirt/46109301/buy">
          NEW La Pajaro Printed Sweatshirt</a>''')
        candidate = self.page.locator("#target")
        self.page.evaluate("document.querySelector('#target').remove()")
        ok, reason = self.mod._verify_resolved_target(self.page, candidate, self.lp, strategy="href")
        self.assertFalse(ok)
        self.assertIn("no longer on the page", reason)

    def test_verified_candidate_dispatches_through_normal_click_path(self):
        href = self.lp["href"]
        self.page.set_content(f'''<main><a id="target" href="{href}">
          <span>NEW</span><h2>La Pajaro Printed Sweatshirt</h2>
          <span>Rs. 475Rs. 999 (52% OFF)</span></a></main>
          <script>document.querySelector('#target').addEventListener('click', e => {{
            e.preventDefault(); document.body.dataset.clicked = 'verified-target';
          }});</script>''')
        step = dict(self.tc["actions"][9])
        step["page_url"] = self.fixture_url
        strategy, found, success, error = self.mod._resolve_and_act_core(self.page, step)
        self.assertTrue(found, (strategy, error))
        self.assertTrue(success, (strategy, error))
        self.assertEqual(self.page.locator("body").get_attribute("data-clicked"), "verified-target")

    def test_formatting_differences_are_compatible(self):
        self.assertTrue(self.mod._names_compatible(
            ["NEW\nLa   Pajaro\nRs. 475"], ["NEW La Pajaro\n\nRs. 475"]
        ))

    def test_duplicate_products_choose_only_exact_recorded_destination(self):
        self.page.set_content('''<main>
          <a href="/sweatshirts/la-pajaro/46109301/buy">NEW La Pajaro Printed Sweatshirt Rs. 475</a>
          <a href="/sweatshirts/la-pajaro/46109302/buy">NEW La Pajaro Printed Sweatshirt Rs. 475</a>
        </main>''')
        loc = self.mod._find_by_href(self.page, self.lp)
        self.assertIsNotNone(loc)
        self.assertEqual(loc.get_attribute("href"), "/sweatshirts/la-pajaro/46109301/buy")

    def test_ambiguous_partial_name_refuses_to_pick_by_position(self):
        self.page.set_content('''<main>
          <a href="/one">La Pajaro Printed Sweatshirt</a>
          <a href="/two">La Pajaro Striped Sweatshirt</a>
        </main>''')
        lp = {"text": "La Pajaro Sweatshirt", "tag": "a", "attributes": {}}
        found = self.mod._find_by_accessible_identity(
            self.page, lp, {"action_type": "click", "bounding_box": {"x": 0, "y": 0, "width": 40, "height": 20}},
            allow_reveal=False,
        )
        self.assertIsNone(found)

    def test_layout_move_does_not_override_verified_identity(self):
        self.page.set_content('''<main><div style="height:1400px">moved</div>
          <a id="target" href="/sweatshirts/la-pajaro/46109301/buy">NEW La Pajaro Printed Sweatshirt</a>
        </main>''')
        self.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        loc = self.mod._find_by_href(self.page, self.lp)
        self.assertIsNotNone(loc)
        self.assertEqual(loc.get_attribute("href"), "/sweatshirts/la-pajaro/46109301/buy")

    def test_missing_target_fails_without_guess(self):
        self.page.set_content('<main><a href="/other">Other product</a></main>')
        self.assertIsNone(self.mod._find_by_href(self.page, self.lp))
        lp = {"text": "La Pajaro Sweatshirt", "tag": "a", "attributes": {}}
        self.assertIsNone(self.mod._find_by_accessible_identity(
            self.page, lp, {"action_type": "click"}, allow_reveal=False
        ))

    def test_unique_exact_name_behavior_remains(self):
        self.page.set_content('<main><a href="/unique">Unique target label</a></main>')
        self.assertTrue(self.mod._names_compatible(["Unique target label"], ["Unique target label"]))
        self.assertFalse(self.mod._names_compatible(["Unique target label"], ["Different target"]))


if __name__ == "__main__":
    unittest.main(verbosity=2)
