# FIX: Capture the Website's Error After a Submit (Field-Error Card)

Date: 14 October 2026. All earlier reports and the code were read first. The failing run's own files were inspected: `generated_scripts/screenshoots/session_20261014_151648_20261014_155649/` (`report.json`, `replay_console.txt`, screenshots) for recording `storage/recordings/session_20261014_151648.json` (12 steps, the last a click on a styled "Sign up" `<div>`). Nothing was run; the only checks were static (Python parse, a compile of a generated replay script from the template, `node --check` of the watcher script, line-ending checks), plus a functional check of the new text-cleaning and server-message functions on synthetic data.

## 1. Root causes

| # | Suspected cause | Verdict and evidence |
|---|---|---|
| 1 | The smart wait after a submit is only about 1 s when there is no next step | **CONFIRMED (the main cause).** `_capture_step_messages()` used `deadline = SUBMIT_MESSAGE_WAIT_S if nlp else 1.0`, and step 12 is the last step. Its screenshot (`feed/step12_sign_up_element_….png`) shows the button **still spinning**: the server check had not answered yet. The end-of-run screenshot (`feed/img2.png`) shows "User already exist" under the form. The wait ended about 1 s after the click, before the message existed, so nothing was captured, and step 12 and the run were PASS. Step 12 itself **was** submit-type (`post_click.submit.fields_before = 3` → `_click_on_filled_form`). |
| 2 | Text / visibility changes in an existing element are not captured | **Partly confirmed (gaps in the code, not the cause in this run).** Text added to an existing element was handled (`check()` on added text nodes / characterData). But: `aria-hidden` was not observed; a visibility change on a *container* only checked the container and its ancestors, never the message element inside it; and an element that was hidden or emptied and later shown again with the **same** text was never reported again (`lastText` dedupe). |
| 3 | Only HTTP 4xx server answers are read | **CONFIRMED in the code:** `_net_record_4xx()` kept only 4xx. Also `_json_message()` only looked into nested objects below the top level, so `data.message` was missed. |
| 4 | Empty messages still logged | **CONFIRMED by the run:** step 10's capture text is `""`, a **private-use icon-font glyph** (an icon inside an error-classed element), which the previous fix's short invisible-character list did not remove. |
| 5 | Other reasons | **Checked, not a cause.** The Phase 5 check (end of every step in `run()`) runs for the last step, for step N in MODE B, and for fast steps. Dedupe (`_MSG_SEEN`, keyed by type + text + second) does not hide a re-shown message on a later attempt (and `_still_visible_message` re-checks after a re-run). The run end is only reached after the end-of-step block. **One related gap:** a message unrelated to the error (or an empty one) could end the smart wait early. Fixed together with 4 (empty ones no longer count) and by the settle rule. |

## 2. Changes made (`generator/script_generator.py` only)

| Function / constant | Change | Why |
|---|---|---|
| `_capture_step_messages()`, the submit wait | It now ends when one of these happens first: **(a)** the next step's target is findable (checked immediately, exactly as before, so no extra delay on success); **(b)** a new website message was captured; **(c)** the page **settled** (`_submit_page_settled`): no fetch / xhr request started by this step still running, and no DOM change for `SUBMIT_SETTLE_S` = 0.8 s, after at least `SUBMIT_MIN_WAIT_S` = 1.0 s; **(d)** the maximum `max(SUBMIT_MESSAGE_WAIT_S, 5.0)` = 5 s. Without a next target, (b)-(d). There is no fast-mode exception. | Cause 1 |
| new `_submit_page_settled()` | Reads the existing `_NET_PENDING` (requests started since the step began, event streams excluded) and the watcher's new last-change time. Any error means "not settled", so the wait ends at its maximum. | Cause 1 (c) |
| `_MSG_WATCHER_JS` (the existing watcher, extended) | **Cleaning:** `clean()` removes every code point that shows nothing readable (controls, format characters such as zero-width / direction marks, variation selectors, BOM, soft hyphen, and private-use icon glyphs), and line breaks / tabs / no-break spaces become spaces. **Last change:** the hidden `window.__afqaMsgLastMut` records the time of the last DOM change. **Child changes:** `childList` changes also check the changed element itself (text put into or taken out of an existing element). **Visibility:** `aria-hidden` is observed too; a class / style / hidden / aria-hidden change also checks the message-like elements **inside** that element (`checkInside`, at most 40, at most once per 200 ms per element, never for html / body). **Re-show:** an element that becomes hidden or empty forgets its last text, so the same text shown again is reported again; the same element + text is never reported twice while it stays shown. The message rules (`classify`) are unchanged. | Causes 2, 4 |
| `_net_record_4xx()` | Also remembers fetch / xhr answers of **any** status (only remembered in the handler; nothing is read there). The list is capped at 60. | Cause 3 |
| `_net_messages_since()` | Reads JSON answers of the step after the step (never in the event handler). Answers declared larger than, or actually larger than, 200 KB are skipped (`_NET_BODY_MAX_BYTES`). The message is cleaned. **4xx answers** are reported as before; **any other status** only when its message matches a configured keyword, so success answers never count. Only the extracted message is kept, never the body. | Cause 3 |
| `_json_message()` | Also looks into nested objects / lists at the top level (for example `data.message`). | Cause 3 |
| new `_clean_msg_text()`; `_norm_msg_text()` now uses it | Generic Unicode categories (`Cc`, `Cf`, `Co`, `Cs`, `Cn` removed, any whitespace collapsed) for both logging and matching. | Cause 4 |
| the `_capture_step_messages()` collector | Every captured text is cleaned. An empty result is not logged, not stored and not checked. The cleaned text is what is logged and matched. | Causes 4, 5 |

**Not changed:**
- `config/message_keywords.json`;
- the Phase 5 card (designs, re-run flow, Attempt N, Retry as is, Stop run, no-answer outcome);
- the early-card fix (cards only after submit-type steps, website text only, aria-invalid only a hint);
- the OTP flow;
- the auto-stop on browser close;
- the banner removal;
- Run Until and fast mode;
- the live log.

## 3. How it works now (MODE A and MODE B identical)

1. **Submit wait:** after any submit-type step (Enter, submit, a submit button, a recorded navigation, or a non-field control clicked on a filled form), the wait continues while the site is still working: its request is pending or the page keeps changing. It ends as soon as the next step's target is there, a message appears, or the page has been quiet for 0.8 s. The maximum is 5 s. The last step, step N, and fast-forwarded steps get exactly the same wait.
2. **Message capture:** the watcher reports a message-like element (alerts, live regions, toast / snackbar / error / warning / invalid / danger classes, field errors) when:
   - it is added;
   - its text changes to a new non-empty value;
   - it becomes visible (itself or through a container).
   
   An element that is hidden or emptied and shown again counts again. Only messages after the step started count, and empty / invisible-only text is never reported.
3. **Server messages:** after the submit-type step, its JSON answers are read safely. 4xx messages are reported as before; other answers only when their message (also from `data.message`-style nesting) matches a keyword.
4. **Phase 5:** the captured message is logged first ("🔔 Captured <type>: <website text>"). Then, if it matches a keyword after this submit-type step and the live log is open, the existing card appears through the pause engine before the step is reported or the run ends.
   - **Continue:** the existing re-run (refill → through the submit step → check again → Attempt N). Then MODE A continues to the end, and MODE B continues fast to N, runs N normally, and stops.
   - **Submit is the last step or step N:** after a successful re-run, the run finishes or stops as usual.

## 4. Backups (`backups/fix_submit_capture/`)

- `backups/fix_submit_capture/generator/script_generator.py`

## 5. Decisions made on my own

1. **Settle = 0.8 s without page changes, after at least 1.0 s, with no pending request started by the step.** Short enough to add little time when the site answers quickly; long enough to catch a server-side check.
2. **A failed / redirected submit whose next target is already on the same page still ends the wait immediately** (rule a, "no extra delay in the success case"). Then the message is not waited for.
3. **Server answers that are not 4xx count only with a keyword match**, so an ordinary `{"message": "Created"}` is never logged or used.
4. **A failed read of the page's last-change time counts as "not settled"**, so the wait then lasts up to its maximum: safe, never shorter than needed.
5. **The descendant check on visibility changes is limited** (40 elements, every 200 ms per element, not for html / body) to keep the watcher light on animated pages.

## 6. Limitations

- A website error that appears more than 5 s after the submit is still missed (the maximum).
- A message element that matches none of the watcher's message rules (no alert / live-region role, no error / warning / toast-like class) is not captured; this rule set is unchanged by design. Its server answer is still read when it carries a keyword.
- A submit whose next step's target is already visible ends the wait at once (rule a).
- Only answers up to 200 KB are read.

## 7. Manual test checklist

- [ ] Sign-up with existing details where the sign-up click is the **last** step, MODE A: after the click the live log shows "🔔 Captured …: <website text>" (for example "User already exist"), then the field-error card appears.
- [ ] The same in MODE B (▶ on the sign-up step = step N).
- [ ] The same with more steps after the sign-up: the run does not continue past the error until the card is answered.
- [ ] Run Until with the sign-up step inside the fast-forward range: the message is captured, the card appears, and after Continue the remaining steps before N run ⏩ FAST.
- [ ] Run Until with the sign-up step as the target step N.
- [ ] New values → Continue → the sign-up succeeds, then the run continues (MODE A) or stops after N (MODE B) correctly.
- [ ] No "🔔 Captured" line with empty text anywhere (for example around date fields with icons).
- [ ] No card during Fill / typing steps.
- [ ] A successful sign-up (new details) is not slower than before.
- [ ] A normal non-sign-up recording: no cards at all.
- [ ] The OTP card works; auto-stop on browser close works.
- [ ] Existing flows unchanged: recording, full replay, Pick Element, validations, live logs, screenshots, the rename popup.
- [ ] Repeat on Windows and macOS.
