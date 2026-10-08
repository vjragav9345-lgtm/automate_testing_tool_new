"""Regressions for preserving overlays that contain position-resolved targets."""
import importlib.util
import json
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from generator.script_generator import generate_script


ROOT = Path(__file__).resolve().parents[1]
RECORDING = ROOT / "storage" / "recordings" / "session_20261007_161821.json"


class OverlayPositionTargetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix="afqa-overlay-position-")
        recording = json.loads(RECORDING.read_text(encoding="utf-8"))
        generated = generate_script(recording, out_name="overlay_position_regression.py", output_dir=Path(cls.temp.name))
        playwright = types.ModuleType("playwright")
        sync_api = types.ModuleType("playwright.sync_api")
        sync_api.sync_playwright = lambda: None
        playwright.sync_api = sync_api
        with patch.dict("sys.modules", {"playwright": playwright, "playwright.sync_api": sync_api}):
            spec = importlib.util.spec_from_file_location("overlay_position_regression", generated)
            cls.replay = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(cls.replay)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_position_resolved_target_inside_popup_prevents_escape_dismissal(self):
        page = object()
        candidate = object()
        step = {
            "action_type": "click",
            "locator_profile": {"tag": "div", "css_path": "div > div:nth-of-type(2)"},
            "bounding_box": {"x": 678, "y": 345, "width": 30, "height": 30},
        }
        with (
            patch.object(self.replay, "_resolve_element", return_value=None),
            patch.object(self.replay, "_find_by_position", return_value=candidate) as find_position,
            patch.object(self.replay, "_live_identity_of", return_value={"parts": [], "href": None}),
            patch.object(self.replay, "_identity_hit_matches", return_value=(True, None)),
            patch.object(self.replay, "_position_candidate_matches", return_value=(True, None)),
            patch.object(self.replay, "_node_in_open_overlay", return_value=True) as in_overlay,
        ):
            self.assertTrue(self.replay._step_target_in_open_overlay(page, step))
        find_position.assert_called_once_with(page, step["locator_profile"], step=step)
        in_overlay.assert_called_once_with(candidate)

    def test_mismatched_position_candidate_does_not_protect_unrelated_overlay(self):
        page = object()
        candidate = object()
        step = {"locator_profile": {"tag": "div"}, "bounding_box": {}}
        with (
            patch.object(self.replay, "_resolve_element", return_value=None),
            patch.object(self.replay, "_find_by_position", return_value=candidate),
            patch.object(self.replay, "_live_identity_of", return_value={"parts": [], "href": None}),
            patch.object(self.replay, "_identity_hit_matches", return_value=(True, None)),
            patch.object(self.replay, "_position_candidate_matches", return_value=(False, "different target")),
            patch.object(self.replay, "_node_in_open_overlay") as in_overlay,
        ):
            self.assertFalse(self.replay._step_target_in_open_overlay(page, step))
        in_overlay.assert_not_called()

    def test_position_fallback_enforces_recorded_image_context_and_sibling_slot(self):
        class Candidate:
            def evaluate(self, _script, *_args, **_kwargs):
                return True

        lp = {
            "tag": "div",
            "content_hint": "image",
            "disambiguation": {
                "container_path": ["div", "div.image-thumb-wrapper-container"],
                "same_text_sibling_index": 4,
            },
        }
        with (
            patch.object(self.replay, "_live_container_path", return_value=["div", "div.image-thumb-wrapper-container"]),
            patch.object(self.replay, "_live_same_text_sibling_index", return_value={"index": 4, "total": 9}),
        ):
            self.assertEqual(self.replay._position_candidate_matches(Candidate(), lp), (True, None))

        with (
            patch.object(self.replay, "_live_container_path", return_value=["div", "div.other-container"]),
            patch.object(self.replay, "_live_same_text_sibling_index", return_value={"index": 4, "total": 9}),
        ):
            ok, reason = self.replay._position_candidate_matches(Candidate(), lp)
        self.assertFalse(ok)
        self.assertIn("different container", reason)

        with (
            patch.object(self.replay, "_live_container_path", return_value=["div", "div.image-thumb-wrapper-container"]),
            patch.object(self.replay, "_live_same_text_sibling_index", return_value={"index": 5, "total": 9}),
        ):
            ok, reason = self.replay._position_candidate_matches(Candidate(), lp)
        self.assertFalse(ok)
        self.assertIn("sibling slot", reason)

        with (
            patch.object(self.replay, "_live_container_path", return_value=["div", "div.image-thumb-wrapper-container"]),
            patch.object(self.replay, "_live_same_text_sibling_index", return_value={"index": 4, "total": 9}),
        ):
            class NonImageCandidate:
                def evaluate(self, _script, *_args, **_kwargs):
                    return False

            ok, reason = self.replay._position_candidate_matches(NonImageCandidate(), lp)
        self.assertFalse(ok)
        self.assertIn("image content", reason)

    def test_reposition_re_resolves_and_hit_tests_current_target(self):
        class Mouse:
            def __init__(self):
                self.moves = []

            def move(self, x, y):
                self.moves.append((x, y))

        class Page:
            def __init__(self):
                self.mouse = Mouse()
                self.waits = []

            def wait_for_timeout(self, duration):
                self.waits.append(duration)

        class Locator:
            def __init__(self):
                self.scrolled = False

            def evaluate(self, *_args, **_kwargs):
                self.scrolled = True

        page = Page()
        old_target = Locator()
        current_target = Locator()
        refresh = Mock(return_value=current_target)
        with (
            patch.object(self.replay, "_wait_next_frames"),
            patch.object(self.replay, "_verify_resolved_target", return_value=(True, None)) as verify,
        ):
            ok, reason, resolved = self.replay._retry_uncovered(
                page, old_target, {"text": "target"}, "text+tag", "covered",
                attempts=1, refresh=refresh,
            )
        self.assertTrue(ok, reason)
        self.assertIs(resolved, current_target)
        self.assertTrue(old_target.scrolled)
        refresh.assert_called_once_with()
        verify.assert_called_once_with(page, current_target, {"text": "target"}, strategy="text+tag")
        self.assertEqual(page.mouse.moves, [(1, 1)])

    def test_persistent_overlay_returns_failure_without_clicking(self):
        class Page:
            class Mouse:
                def move(self, *_args):
                    pass
            mouse = Mouse()

            def wait_for_timeout(self, *_args):
                pass

        class Locator:
            clicked = False

            def evaluate(self, *_args, **_kwargs):
                pass

            def click(self, *_args, **_kwargs):
                self.clicked = True

        page = Page()
        target = Locator()
        with (
            patch.object(self.replay, "_wait_next_frames"),
            patch.object(self.replay, "_verify_resolved_target", return_value=(False, "not hit-testable: covered")),
        ):
            ok, reason, resolved = self.replay._retry_uncovered(
                page, target, {"text": "target"}, "text+tag", "covered",
                attempts=1, refresh=lambda: target,
            )
        self.assertFalse(ok)
        self.assertIn("not hit-testable", reason)
        self.assertIs(resolved, target)
        self.assertFalse(target.clicked)


if __name__ == "__main__":
    unittest.main(verbosity=2)
