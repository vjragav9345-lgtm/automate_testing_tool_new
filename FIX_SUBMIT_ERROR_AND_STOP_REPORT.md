# FIX: Field-Error Card Only After Submit, Robust Matching, Auto-Stop on Browser Close

Date: 14 October 2026. PHASE_1-6 reports, FIX_OTP_GENERIC_REPORT.md and the code were read first. Nothing was run; the only checks were static (Python parse, a compile of a generated replay script from the template, `node --check` on the watcher script and `run_control.js`, line-ending checks), plus a functional check of the changed matching / identification functions on synthetic data (Section 3).

## 1. Confirmed root causes

**A - the card at a Fill step.** All in `generator/script_generator.py`:

- **Watcher:** `_MSG_WATCHER_JS` turned an input becoming `aria-invalid="true"` into a *message* with the **tool's own text** "Field marked invalid: <label>". Many date / masked inputs flip `aria-invalid` while being typed into.
- **Card check:** the Phase 5 check in `run()` (end of step) evaluated `_STEP_CAPTURED` after **every** step, not only submit-type steps.
- **Keywords:** `_message_matches_keyword()` matched "invalid" (then in `config/message_keywords.json`) inside that tool text, so the card opened while typing.

**B - the website's error was missed or put on the wrong field:**

- **Matching:** keywords were plain lowercase substrings, and the list had "already exists", so "User already exist" did not match.
- **Field link:** the watcher's `nearInput()` linked a message to an input by **proximity** (the single input in the same small container), and `_identify_field()` used that link. A message placed under an unrelated input produced a single-field card for that unrelated field.

**C - the run did not end and the banner stayed:**

- **Relaunch:** `run()`'s per-step crash handler explicitly treats "the browser died or every registered page closed" as a crash and **relaunches a new browser**, then continues.
- **Waiting cards:** `_pause_and_ask()` (OTP / failure / field-error cards) kept waiting up to 180 s, because `page.wait_for_timeout` failed and it just slept.
- **Run lock:** the run therefore stayed in `executor.run_execution._active_replays` (not done). `/api/test/run/active` kept reporting it active, so `static/js/run_control.js` kept the banner and the disabled buttons.

## 2. Changes made

### `generator/script_generator.py`

| Function | Change | Why |
|---|---|---|
| `_MSG_WATCHER_JS` (watcher) | `clean()` removes invisible characters (zero-width space / joiners, word joiner, BOM, soft hyphen) and treats no-break spaces as spaces, so an "empty" element is never a message. New `linkedInput()`: an input whose `aria-describedby` / `aria-errormessage` names the message element (or one of its 3 nearest ancestors). Records carry `input` = **explicit link only**, and `near_input` = proximity (a hint, unused for naming). An input turning `aria-invalid="true"` is now recorded as `{type: "invalid field", text: "", hint: true, input}`: **no tool-generated text**. `__afqaMsgScan()` reports the same fields. | A, B |
| `_capture_step_messages()` | Hints go to the new `_STEP_INVALID_HINTS` (never logged, never a message). Messages whose normalized text is empty are dropped. | A, empty messages |
| new `_click_on_filled_form()`, used by `_is_submit_type_step()` | Also counts as submit-type: a click on a control that is not a field or a choice (not input / textarea / select / label, not checkbox / radio / switch / textbox / combobox / option-like roles), made while the page's text fields held values (the recorder's own `post_click.submit.fields_before > 0`). Covers forms sent by a styled `<div>` button. | Required behaviour 2 (the card after the step that sends the form) |
| new `_norm_msg_text()`; `_message_keywords()`, `_message_matches_keyword()` | Message and keywords are normalized the same way: lowercase, invisible characters removed, whitespace runs collapsed, trimmed. Each keyword is matched as a substring of the message. | B (robust matching) |
| `_fill_field_type()` | Adds the field type `name` (label words name / fullname / firstname / lastname / surname). | Task 3 (a message naming "name") |
| `_identify_field(msg, cands, steps, invalid_hints)` | One field only via an explicit link: (1) `msg.input` from aria-describedby / aria-errormessage; (2) exactly one of the form's inputs became `aria-invalid` during the submit step; (3) the message names email / phone / mobile / username / name and exactly one field has that type. Proximity is never used, so the **all-fields card** appears otherwise. | B |
| `run()`, Phase 5 trigger | The field-error card is evaluated **only when `_is_submit_type_step(step)`**, only for non-hint website messages, with the normalized keyword match, and identification gets the step's aria-invalid hints. Messages captured at Fill / typing / click-into-field steps are only logged ("🔔 Captured …"), never a card. | A, required behaviour 1-2 |
| new `_watch_replay_browser()`, `_replay_browser_gone()`, `_clear_pending_card_files()`, `BROWSER_CLOSED_REASON`; registered right after the replay context's first page is created | Uses Playwright's `browser.on("disconnected")`, `context.on("close")`, `browser.is_connected()` and `page.is_closed()` for every context page. Any error reads as "not gone" (existing behaviour). | C |
| `_pause_and_ask()` | Every wait round, and whenever the page wait fails, checks `_replay_browser_gone()`. If gone, the wait ends **at once** with `{"action": "stop", "browser_closed": True}`, the pending answer / OTP files are removed, and `awaiting_otp` and the card are cleared. | C (also while any card waits) |
| `_wait_for_live_otp()` | Logs "The browser window was closed - no OTP needed any more" instead of "no OTP entered within 180s" in that case. Otherwise unchanged. | C (clear log) |
| `run()`: top of each step, end of each step, after the field-error and fallback card answers, and the crash handler (before its relaunch) | If the browser is gone, the run stops: the current step gets "Stopped: The browser window was closed. The replay stopped.", `result["browser_closed"] = True`, a live-log line, and the remaining steps are "NOT RUN (the browser window was closed)" through the existing backfill. The crash handler **no longer relaunches a browser the user closed**; it stops instead. A recorded Close Tab step that closes the last page is the recording's own doing, so then only a disconnected browser counts. | C |

### Other files

| File : function | Change | Why |
|---|---|---|
| `executor/run_execution.py`: `_finalize_result()` | `browser_closed` is carried into the final result. Such a run is never PASS, and its message is "The browser window was closed, so the run stopped". The run is finalized as soon as the replay process exits, which releases the run lock. | C |
| `app.py`: `/api/test/run/stream` summary | The plain summary says "The browser window was closed, so the run stopped." (prefixed "Partial run (until step N):" in MODE B). | C (live log shows it finished) |
| `static/js/run_control.js` | The floating "Running: … [Stop run]" banner and its Stop button are **removed**. Disabling and re-enabling the Replay buttons and ▶ icons (`data-af-run-control`), the 1.5 s poll and the `window.AFRunControl` API are kept. | Required behaviour 6 |
| `templates/index.html`, `templates/recording_editor.html` | `run_control.js?v=1` → `?v=2`, so browsers load the new file. | cache |
| `config/message_keywords.json` | New generic stems; broad words removed (Section 4). | B |

**Unchanged:**
- the OTP flow (detection, split boxes, the 180 s window, masked input, Submit, Stop, never logged);
- the card designs (single / all fields, empty boxes, "Use for this run only" default, "Save to recording", Continue / Retry as is / Stop run);
- the re-run flow with Attempt 2…;
- the live log's own Stop run button and the cards' Stop run.

## 3. How it works now (MODE A and MODE B identical; all in the single replay loop)

- **Trigger:**
  - After a step, Phase 4 still logs captured website messages ("🔔 Captured <type>: <text>").
  - The field-error card is evaluated **only when that step is submit-type** (Enter, submit, a submit button, a recorded navigation, or a non-field control clicked on a filled form). It also covers its smart wait and a re-run's re-check.
  - It opens only for a real website message (visible alert / toast / live-region / field-error text, or a server 4xx JSON message) that contains a keyword.
  - An input merely turning aria-invalid is never a message. Fill / typing / click-into-field steps never open a card.
- **Keyword matching:** `_norm_msg_text` on both sides, substring match, with keywords only from the config file.
- **Field identification:** an explicit aria link, else exactly one input turned aria-invalid during the submit step, else exactly one field of a named type (email, phone, username, name). Otherwise the all-fields card for that form.
- **After Continue:** unchanged re-run flow (refill the changed fields → re-run through the submit step → re-check → "Attempt N" → continue). Fast before N in MODE B.
- **Auto-stop:**
  - When the window / last page is closed or the browser disconnects, the next check stops the run immediately. The checks run before a step, after a step, inside every card wait (each round, about 0.5 s), and in the crash handler.
  - The step and remaining steps are reported as above. The script writes its final result and exits, the executor finalizes the run, and the live log gets its summary.
  - The Replay buttons and ▶ icons re-enable within about 1.5 s (the existing poll).

**Functional check** (synthetic data, the template's own functions):

- **Matching:**

| Text | Matches a keyword? |
|---|---|
| "User already exist" | yes |
| "This email is ALREADY  REGISTERED." | yes |
| "Mobile number is already in use" | yes |
| "Field marked invalid: …" | no |
| "Invalid OTP, try again" | no |
| invisible-only text | no |
| "Not available in your area" | no |

- **Submit-type:**

| Step | Submit-type? |
|---|---|
| a div button clicked on a filled form | yes |
| a click into an input | no |
| a fill | no |
| a checkbox | no |

- **Identification:**

| Case | Result |
|---|---|
| A message only near the date field | no field (all-fields card) |
| Explicit link to email | the email step |
| Only the mobile input turned aria-invalid | the mobile step |
| "Email already exists" | the email step |
| "Name already taken" | the full-name step |

## 4. Final `config/message_keywords.json`

```json
{
    "_comment": "Generic words/phrases that mark a WEBSITE message (visible alert, toast, live region, field error text, or a server error response) as an 'account already exists' or field error during replay. Only checked after a step that submits a form. Matching ignores case, extra spaces and invisible characters, and a keyword only has to be part of the message (so 'already exist' also matches 'already exists'). Edit freely: one entry per word or phrase. No site-specific text.",
    "keywords": [
        "already exist",
        "already registered",
        "already in use",
        "already taken",
        "already been taken",
        "already used",
        "already have an account",
        "is registered",
        "is taken"
    ]
}
```

(Removed: "invalid", "try again", "not available", and "already exists" / "already exist" are merged into the stem "already exist".)

## 5. Backups (`backups/fix_submit_error_stop/`)

- `backups/fix_submit_error_stop/generator/script_generator.py`
- `backups/fix_submit_error_stop/executor/run_execution.py`
- `backups/fix_submit_error_stop/app.py`
- `backups/fix_submit_error_stop/config/message_keywords.json`
- `backups/fix_submit_error_stop/static/js/run_control.js`
- `backups/fix_submit_error_stop/templates/index.html`
- `backups/fix_submit_error_stop/templates/recording_editor.html`

## 6. Decisions made on my own

1. **One shared submit-type definition** (`_is_submit_type_step`, extended by `_click_on_filled_form`) for both the Phase 4 smart wait and the Phase 5 card. A form sent by a styled button then gets the same message wait as a real submit button, so its error is not missed.
2. **Disconnecting no longer relaunches a browser.** The requirement treats a disconnected browser as "closed" and asks to stop. The old one-time relaunch remains only for a broken page while the browser is still connected and a page is still open.
3. **"Stopped" wording:** the current step is reported as failed with "Stopped: The browser window was closed. The replay stopped." The remaining steps use the existing NOT RUN reporting. This matches how a user Stop and a failure are already reported.
4. **Close Tab exception:** a recorded Close Tab that closes the last page does not count as "the user closed the browser" (only a disconnect does then). Otherwise a recording ending with Close Tab would be reported as stopped.
5. **The banner's CSS rules in `static/css/style.css` were left in place.** They are unused now; removing them is not needed and touches another file.

## 7. Limitations

- **Older recordings:** they lack `post_click.submit.fields_before`, so a form sent by a styled non-button control is only submit-type there if it navigated / was recorded as a submit. Otherwise no field-error card (messages are still logged).
- **Unlinked messages:** a website message not linked to a field by an ARIA attribute, with no single aria-invalid input and no field-type word, always gives the all-fields card (by design).
- **Long waits inside a step:** a step's own waits (for example a chatbot reply wait) end when their Playwright calls fail on the closed page, usually at once. A wait that only sleeps can take up to its own bound before the next check.
- **Re-enable delay:** the Replay buttons re-enable on the next 1.5 s poll after the run ends.

## 8. Manual test checklist

- [ ] Sign-up replay with a date field and other fields, MODE A: no card while filling (the date field's aria-invalid never opens a card).
- [ ] The same in MODE B (▶ on a step after the sign-up click): no card while filling.
- [ ] Sign-up with existing details: after the sign-up click the live log shows "🔔 Captured …: <website text>" (for example "User already exist"), then the card appears. New values → Continue → the fields refill, the sign-up re-runs, and the flow completes. Repeated error → "Attempt 2".
- [ ] An error message placed under an unrelated field (no aria link): the ALL-FIELDS card appears, not a single card for that field.
- [ ] A normal non-sign-up recording: no field-error cards at all.
- [ ] The OTP card and OTP flow still work (MODE A and MODE B).
- [ ] Close the replay browser during a normal step: the run stops at once; the live log shows "The browser window was closed - the run stopped…" and the summary; the rest are NOT RUN; Replay buttons and ▶ re-enable.
- [ ] Close it while the field-error card waits: the card disappears; the same stop.
- [ ] Close it during the OTP wait: the OTP card disappears; the same stop.
- [ ] No floating "Running… Stop run" banner on the dashboard or in the editor; the live log's Stop run still works.
- [ ] Existing flows unchanged: recording, full replay, Run Until, Pick Element, validations, live logs, screenshots, the rename popup, the failure card.
- [ ] Repeat on Windows and macOS.
