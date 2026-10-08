"""Focused regression for overlay recovery on actions recorded inside a modal."""
import unittest
from pathlib import Path
import sys
import importlib.util
import tempfile
from types import ModuleType

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from generator.script_generator import generate_script


class _Keyboard:
    def __init__(self):
        self.presses = []

    def press(self, key):
        self.presses.append(key)


class _Locator:
    def count(self):
        return 0


class _Page:
    def __init__(self):
        self.keyboard = _Keyboard()
        self.locator_calls = []

    def locator(self, selector):
        self.locator_calls.append(selector)
        return _Locator()


class RecordedModalRecoveryCheck(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._tmp = tempfile.TemporaryDirectory(prefix="autoflow_modal_recovery_")
        path = generate_script(
            {"name": "modal_recovery", "start_url": "about:blank", "actions": []},
            out_name="modal_recovery.py",
            output_dir=Path(cls._tmp.name),
        )
        # The generated runner imports Playwright at module load, but these
        # unit checks exercise only its recovery helper and do not launch a browser.
        playwright = ModuleType("playwright")
        sync_api = ModuleType("playwright.sync_api")
        sync_api.sync_playwright = lambda: None
        playwright.sync_api = sync_api
        sys.modules.setdefault("playwright", playwright)
        sys.modules.setdefault("playwright.sync_api", sync_api)
        spec = importlib.util.spec_from_file_location("modal_recovery_generated", path)
        cls.generated = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.generated)

    @classmethod
    def tearDownClass(cls):
        cls._tmp.cleanup()

    def test_recorded_modal_action_does_not_escape_or_search_close_controls(self):
        page = _Page()

        self.generated._try_dismiss_overlay(page, {"in_modal": True})

        self.assertEqual(page.keyboard.presses, [])
        self.assertEqual(page.locator_calls, [])

    def test_unexpected_overlay_recovery_still_uses_escape(self):
        page = _Page()
        original = self.generated._step_target_in_open_overlay
        self.generated._step_target_in_open_overlay = lambda *_args: False
        try:
            self.generated._try_dismiss_overlay(page, {"in_modal": False})
        finally:
            self.generated._step_target_in_open_overlay = original

        self.assertEqual(page.keyboard.presses, ["Escape"])
        self.assertTrue(page.locator_calls)


if __name__ == "__main__":
    unittest.main()
