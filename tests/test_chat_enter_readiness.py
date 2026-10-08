"""Focused regression coverage for chat Enter submission readiness."""
import importlib.util
import json
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from generator.script_generator import generate_script


class ChatEnterReadinessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._temp = tempfile.TemporaryDirectory(prefix="autoflow-chat-enter-")
        recording = json.loads((ROOT / "storage/recordings/session_20261007_111714.json").read_text(encoding="utf-8"))
        generated = generate_script(recording, out_name="chat_enter_test_script.py", output_dir=Path(cls._temp.name))
        spec = importlib.util.spec_from_file_location("chat_enter_test_script", generated)
        cls.replay = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.replay)

    @classmethod
    def tearDownClass(cls):
        cls._temp.cleanup()

    def setUp(self):
        self.replay._STEP_DETAILS.clear()
        self.replay._STEP_WARNINGS.clear()
        self.replay._CHAT_STATE.update({
            "idle_fp": None, "input_lp": None, "typed": None, "lines_before": None,
            "net_before": None, "url": None, "handled": None, "reply": None,
            "defer": None, "defer_old": None, "interrupted": False, "old_after_send": None,
            "sent_at": None, "nxt_before": None, "wait_end": None, "busy_seen": None,
            "stop_secs": None, "stop_pending": None, "ctrl_before": None, "origin": None,
        })

    def test_busy_control_remains_busy_past_old_six_second_cap_until_idle(self):
        # The real helper observes a control fingerprint. This simulated sequence isolates
        # its clock rule; real keyboard and DOM effects are covered below when Chromium exists.
        page = _SleepingPage()
        self.replay._CHAT_STATE["idle_fp"] = "idle"
        self.replay._CHAT_STATE["ctrl_before"] = "idle"
        started = time.monotonic()
        with patch.object(self.replay, "CHAT_REPLY_SETTLE_S", 0.05), \
             patch.object(self.replay, "CHAT_REPLY_MAX_S", 1.2), \
             patch.object(self.replay, "_chat_text_sig", return_value="stable reply"), \
             patch.object(self.replay, "_chat_same_document", return_value=True), \
             patch.object(self.replay, "_chat_fp_now", side_effect=lambda _page: (
                 "busy-a" if time.monotonic() - started < 0.2 else
                 ("busy-b" if time.monotonic() - started < 0.42 else "idle")
             )):
            waited = self.replay._chat_wait_reply_done(page, {})
        self.assertGreaterEqual(waited, 0.38)
        self.assertEqual(self.replay._CHAT_STATE["wait_end"], "finished")

    def test_retry_is_skipped_when_prompt_is_already_visible(self):
        with patch.object(self.replay, "_chat_typed_text_on_page", return_value=True), \
             patch.object(self.replay, "_chat_wait_page_idle") as wait_idle:
            result = self.replay._chat_resend_once(object(), {"action_type": "press"}, {}, "first failure")
        self.assertIsNone(result)
        wait_idle.assert_not_called()

    def test_shift_enter_retains_multiline_semantics(self):
        self.assertFalse(self.replay._chat_is_send_step(
            {"action_type": "press", "value": "Shift+Enter", "locator_profile": {"tag": "textarea"}},
            {"action_type": "fill", "locator_profile": {"tag": "textarea"}},
        ))

    def test_pincode_form_result_is_not_classified_as_chat_send(self):
        recording = json.loads((ROOT / "storage/recordings/session_20261007_153501.json").read_text(encoding="utf-8"))
        with tempfile.TemporaryDirectory(prefix="autoflow-pincode-chat-") as temp:
            generated = generate_script(recording, out_name="pincode_chat_test_script.py", output_dir=Path(temp))
            spec = importlib.util.spec_from_file_location("pincode_chat_test_script", generated)
            replay = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(replay)
        fill, submit = replay.STEPS[28], replay.STEPS[29]
        self.assertEqual(fill["value"], "641025")
        self.assertTrue(submit["message_echoed"])  # recorded false positive from the form result
        self.assertFalse(replay._chat_is_send_step(submit, fill))

    def test_explicit_single_line_message_input_remains_a_chat_editor(self):
        profile = {"tag": "input", "attributes": {"type": "text", "name": "message"}}
        self.assertTrue(self.replay._chat_conversation_editor(profile))
        self.assertFalse(self.replay._chat_conversation_editor(
            {"tag": "input", "attributes": {"type": "text", "name": "pincode"}}
        ))

    def test_unsubmitted_text_remains_a_failure(self):
        with patch.object(self.replay, "EFFECT_VERIFY_TIMEOUT_S", 0):
            self.assertIn("nothing was sent", self.replay._check_submit_result(
                _StaticSubmitPage({"cleared": False, "added": 0}),
                {"action_type": "press", "value": "Enter", "name": "message", "post_click": {"submit": {"field_cleared": True}}},
                {"rule": "cleared", "url": "about:blank"},
            ))

    def test_browser_keyboard_submission_and_async_clear(self):
        page = self._browser_page_or_skip()
        page.set_content(_CHAT_HTML)
        textarea = page.locator("#prompt")
        step = {"action_type": "press", "value": "Enter", "name": "message",
                "post_click": {"submit": {"fields_before": 1, "field_cleared": True, "content_added": True}}}
        status, message = self.replay._fill_with_page_awareness(page, textarea, "hello from a real key")
        self.assertEqual(status, "typed", message)
        self.assertFalse(page.locator("#send").is_disabled())
        snap = self.replay._submit_snapshot(page, step)
        textarea.press("Enter")
        self.assertIsNone(self.replay._check_submit_result(page, step, snap))
        self.assertEqual(page.locator(".sent").inner_text(), "hello from a real key")
        self.assertEqual(textarea.input_value(), "")

    def test_browser_waits_for_busy_state_and_reresolves_replaced_textarea(self):
        page = self._browser_page_or_skip()
        page.set_content(_CHAT_HTML)
        original = page.locator("#prompt")
        self.replay._CHAT_STATE["idle_fp"] = original.evaluate(self.replay._CHAT_FP_JS)
        self.replay._CHAT_STATE["ctrl_before"] = self.replay._CHAT_STATE["idle_fp"]
        self.replay._CHAT_STATE["lines_before"] = set(page.evaluate(self.replay._CHAT_LINES_JS) or [])
        self.replay._CHAT_STATE["origin"] = page.evaluate("performance.timeOrigin")
        status, message = self.replay._fill_with_page_awareness(page, original, "wait then send")
        self.assertEqual(status, "typed", message)
        page.evaluate("""() => {
          const b = document.querySelector('#send'); window.chatBusy = true; b.disabled = true; b.setAttribute('aria-label', 'Stop');
          document.querySelector('#status').textContent = 'Working';
          const old = document.querySelector('#prompt'); const replacement = old.cloneNode(true);
          old.replaceWith(replacement);
          setTimeout(() => { window.chatBusy = false; b.disabled = false; b.setAttribute('aria-label', 'Send');
            document.querySelector('#status').textContent = 'Ready'; }, 650);
        }""")
        started = time.monotonic()
        with patch.object(self.replay, "CHAT_REPLY_SETTLE_S", 0.05), \
             patch.object(self.replay, "CHAT_REPLY_MAX_S", 2.0), \
             patch.object(self.replay, "_chat_fp_now", side_effect=lambda pg: pg.locator("#prompt").evaluate(self.replay._CHAT_FP_JS)):
            self.replay._chat_wait_reply_done(page, {})
        self.assertGreaterEqual(time.monotonic() - started, 0.6)
        live_textarea = self.replay._resolve_element(page, {"id": "#prompt", "tag": "textarea"})
        self.assertIsNotNone(live_textarea)
        self.assertEqual(live_textarea.count(), 1)
        live_textarea.press("Enter")
        self.assertEqual(page.locator(".sent").inner_text(), "wait then send")

    def _browser_page_or_skip(self):
        try:
            from playwright.sync_api import sync_playwright
            if not hasattr(self, "_pw"):
                self._pw = sync_playwright().start()
                self.addCleanup(self._pw.stop)
                try:
                    self._browser = self._pw.chromium.launch(headless=True)
                except Exception as exc:
                    self.skipTest(f"Chromium could not be launched in this environment: {exc}")
                self.addCleanup(self._browser.close)
            return self._browser.new_page()
        except ImportError as exc:
            self.skipTest(f"Playwright is unavailable: {exc}")

    def test_browser_rejects_unsubmitted_enter_and_keeps_failure(self):
        page = self._browser_page_or_skip()
        page.set_content(_CHAT_HTML)
        textarea = page.locator("#prompt")
        step = {"action_type": "press", "value": "Enter", "name": "message",
                "post_click": {"submit": {"fields_before": 1, "field_cleared": True}}}
        self.replay._fill_with_page_awareness(page, textarea, "do not send")
        page.evaluate("document.querySelector('#send').disabled = true")
        snap = self.replay._submit_snapshot(page, step)
        textarea.press("Enter")
        with patch.object(self.replay, "EFFECT_VERIFY_TIMEOUT_S", 0):
            failure = self.replay._check_submit_result(page, step, snap)
        self.assertIn("nothing was sent", failure)
        self.assertEqual(page.locator(".sent").count(), 0)

    def test_browser_shift_enter_keeps_multiline_text_without_sending(self):
        page = self._browser_page_or_skip()
        page.set_content(_CHAT_HTML)
        textarea = page.locator("#prompt")
        self.replay._fill_with_page_awareness(page, textarea, "first line")
        textarea.press("Shift+Enter")
        textarea.press_sequentially("second line")
        self.assertEqual(page.locator(".sent").count(), 0)
        self.assertEqual(textarea.input_value(), "first line\nsecond line")

    def test_browser_can_take_an_unrelated_followup_action_after_send(self):
        page = self._browser_page_or_skip()
        page.set_content(_CHAT_HTML + "<button id='next'>Next</button>")
        textarea = page.locator("#prompt")
        self.replay._fill_with_page_awareness(page, textarea, "send before next")
        textarea.press("Enter")
        page.locator("#next").click()
        self.assertEqual(page.locator(".sent").inner_text(), "send before next")
        self.assertEqual(page.locator("#next").evaluate("e => e.matches(':focus')"), True)


class _SleepingPage:
    url = "about:blank"

    def wait_for_timeout(self, milliseconds):
        time.sleep(milliseconds / 1000)


class _StaticSubmitPage:
    url = "about:blank"

    def __init__(self, result):
        self.result = result

    def evaluate(self, _script):
        return self.result

    def wait_for_timeout(self, _milliseconds):
        pass


_CHAT_HTML = """<!doctype html><html><body>
<div id="status">Ready</div><textarea id="prompt"></textarea>
<button id="send" aria-label="Send" disabled>↑</button><div id="messages"></div>
<script>
const button = document.querySelector('#send');
window.chatBusy = false;
document.addEventListener('input', event => { if (event.target.id === 'prompt') button.disabled = !event.target.value || window.chatBusy; });
document.addEventListener('keydown', event => {
  if (event.target.id !== 'prompt') return;
  if (event.key !== 'Enter' || event.shiftKey || button.disabled) return;
  event.preventDefault(); const input = event.target, text = input.value; button.disabled = true;
  setTimeout(() => { const p = document.createElement('p'); p.className = 'sent'; p.textContent = text;
    document.querySelector('#messages').appendChild(p); input.value = ''; input.dispatchEvent(new Event('input', {bubbles:true}));
    button.disabled = window.chatBusy || !input.value; }, 80);
});
</script></body></html>"""


if __name__ == "__main__":
    unittest.main()
