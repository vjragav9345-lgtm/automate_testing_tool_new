# Phase 4 Report: Message Capture (detection only)

Date: 14 October 2026. Only Phase 4 was implemented. Nothing was run; the only check was static (a compile of a generated replay script from the template).

## 1. Step 0 findings relevant to this phase

- **Reused from earlier phases:**
  - Phase 1: the live log channel and step results;
  - Phase 2: `_FAST_MODE`;
  - Phase 3: the pause engine (not used here, because this phase never pauses).
- **Where replay pages come from:** every replay page and tab belongs to the context created in the generated script's `run()`, plus the one created on crash recovery.
  - That context already gets `add_init_script` (the `navigator.share` neutraliser) and `_net_track` (pending requests).
  - The recorder (`recorder/record_session.py`) and Pick Element (`app.py`, `recorder/pick_element.py`) create their **own** contexts and never call `run()`. So anything installed in `run()` is active **only during replays**.
- **When a step ends:** each step ends in one place, which runs for passed and failed steps alike, right before the step screenshot. That is where the step's own outcome is final and the page is still as the step left it.
- **Submit steps:** "submit-type" can be told from the recording: Enter, a `submit` step, a click whose recorded result was `submit_like` / `submits_form`, a recorded navigation (`_step_expects_navigation`), or a target with `type="submit"`.
- **Waits:** the replay already waits for page and element readiness after a step. The next step's target can be checked without acting through the existing `_locator_findable()`.

## 2. What was changed (all in `generator/script_generator.py`)

| Function / constant | Change | Reason |
|---|---|---|
| `_MSG_WATCHER_JS` (new) | The init script: a `MutationObserver` on the whole document. It records newly appearing (visible) message elements: `role=alert` / `alertdialog`, `aria-live` regions (not "off"), and elements whose class names toast / snackbar / error / invalid / danger / warning, including text that changes inside them. It also records inputs that become `aria-invalid="true"`. Each record has its text, type, time and associated input (`aria-describedby` / `aria-errormessage`, else the single input in the same small container), with a selector (`#id` or `tag[name=…]`), name, type and label. Records are kept in a hidden, non-enumerable `window.__afqaMsgWatch` (at most 200), so short-lived toasts are not missed. It never changes the page. | Watcher. |
| `_msg_capture_install()` (new); called in `run()` on the replay context and on the crash-recovery context | `context.add_init_script(watcher)` (every page and every new tab), plus a `response` listener. | Only replay contexts get it. |
| `_net_record_4xx()`, `_net_messages_since()`, `_json_message()` (new) | Remember HTTP 4xx answers of fetch / xhr / page requests. After a submit-type step, read their bodies **from the replay's own flow** (not inside the event handler), only when the content type is JSON. Take the first `message` / `error` / `detail` / `errors` (…) text. Anything unreadable is ignored. | Network capture. |
| `_is_submit_type_step()` (new) | The recorded signals listed in Section 1. | Which steps get the smart wait and network capture. |
| `_capture_step_messages()` (new); called at the end of every step, before its screenshot | Collects the messages from every open page whose time is **at or after this step's start** (static page text never counts), plus the 4xx messages after a submit-type step. **Smart wait** after a submit-type step: it polls every 200 ms and ends at once when the next step's target is findable or a new message appears, at most `SUBMIT_MESSAGE_WAIT_S` = 5 s (1 s when the next step has no target, e.g. a navigate). Fast mode does not shorten it. Each new message is logged once as **"🔔 Captured <type>: <text>"**, with one screenshot at that moment (`<run folder>/captured_messages/stepNN_message_HH-MM-SS.png`). Wrapped: any error only prints a warning. | Detection and logging only. |
| Per-step reset (`_STEP_CAPTURED.clear()`); the step result gets `"captured_messages"` | The captured records (type, text, input, HTTP status, screenshot) are kept on the step's result. | Data for Phase 5. Pass / fail unchanged. |

Nothing pauses, no value is changed, and no step's pass / fail is affected.

## 3. MODE A and MODE B

- The watcher, network capture, smart wait and logging run inside the single replay loop for every step, so they behave identically in both modes.
- In MODE B the fast steps get the same capture and the same smart wait (fast mode only removes per-step screenshots). The capture screenshot is taken in fast mode too, because it belongs to the captured message, not to the step.

## 4. Backup files created (`backups/phase_4/`)

- `backups/phase_4/generator/script_generator.py`

## 5. Decisions made on my own

1. **Response bodies are read after the step**, from the replay's own code path, not inside the Playwright event handler. Blocking calls inside sync-API event handlers are unsafe.
2. **Only JSON 4xx answers of fetch / xhr / page requests are logged** (images, scripts and similar are ignored). A JSON 4xx without a readable message field is not logged.
3. **The smart wait is bounded at 5 s** (1 s when the next step has no target). It ends immediately in the normal success case.
4. **A message counts only when visible** when it appears (or becomes visible later through a class / style / hidden change). Its text must be new for that element, so repeated identical updates are logged once.
5. **The capture screenshot goes into its own `captured_messages` folder** in the run folder. Step screenshots and their naming are unchanged.

## 6. Skipped / not possible

- Messages **inside iframes** are watched by the init script (it runs in every frame) but are only read from each page's top frame.
- The browser's own native validation bubbles are not part of the page, so they cannot be observed. Inputs that become `aria-invalid="true"` are captured, together with their `validationMessage`.

## 7. Known limitations

- Class-name matching is generic (toast / snackbar / error / invalid / danger / warn). A site whose message elements use none of these, and no ARIA role / live region, is not captured.
- A message that appears and disappears within the same step is still logged (it is stored when it appears). Its screenshot, taken when the replay reads the records, may no longer show it.
- A step that loads a new page counts messages shown on that new page as appearing after the step started.
- On pages with very heavy class / style animation, the observer does a small amount of extra work per change.

## 8. Manual test checklist

**MODE A**

- [ ] Replay a recording where submitting a form shows an error toast or alert (for example a sign-up with an existing email): the live log shows "🔔 Captured toast/alert/error: <text>" under the submit step, and a screenshot appears in `<run folder>/captured_messages/`. The run's pass / fail is the same as before.
- [ ] A field error next to an input, or an input turning `aria-invalid`: "🔔 Captured field error / invalid field: …", and the step's `captured_messages` in `report.json` names the input (selector, label).
- [ ] A form whose server answers 4xx with JSON `{"message": …}`: "🔔 Captured server response: …".
- [ ] A normal successful submit: no captured line, and no noticeable extra delay (the next step starts as soon as its target is there).
- [ ] Static error text already on the page before a step is never logged.

**MODE B**

- [ ] ▶ on a step after a failing submit: the fast steps show the same "🔔 Captured …" lines and screenshots; step N then runs normally and the run stops.

**Existing flows**

- [ ] Recording: no watcher in the recording browser; recording works as before.
- [ ] Full replay, Pick Element and validations work as before.
- [ ] OTP card (Phase 3), live log, summary, timestamped step screenshots, the HTML report, the rename popup, and old recordings open and replay.
- [ ] Repeat on Windows and macOS.
