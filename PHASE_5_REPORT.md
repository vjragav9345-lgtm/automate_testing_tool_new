# Phase 5 Report: Account-Exists / Field Error Handling

Date: 14 October 2026. Only Phase 5 was implemented, plus one Phase 4 defect fix (Section 2, last row). Nothing was run; the only checks were static (Python parse, a compile of a generated replay script from the template, `node --check`, a Jinja parse), plus a unit check of the new field helpers on synthetic steps.

## 1. Step 0 findings relevant to this phase

- **Reused:**
  - Phase 4: the captured messages of each step (`_STEP_CAPTURED`), with their type, text and input (selector, id, name, label).
  - Phase 3: `_pause_and_ask()`, the pinned card, `_viewer_present()`, `_StepCursor`, the answer endpoint, and the retry handling in the live-log stream.
  - Phase 2: `_FAST_MODE` and the Stop file.
- **Recorded Fill steps:** the step's value; `locator_profile` (id, name, placeholder, nearby_label, aria_label, `attributes`: type, autocomplete, name, id); `page_url`; `timestamp`.
- **Form membership is not recorded,** so it is read from the live page when the card is built: the submit element's `form`, and whether each Fill step's resolved input is inside it.
- **Saving:** the editor saves through `repository._write_json` (atomic). A run's recording file was not remembered by the server, so it is now kept in the run's metadata.
- **Phase 4 defect found:** its inserted code block had been written with doubled line endings (`\r\r\n`, 287 lines). The script still compiled, because Python reads a lone `\r` as a newline, but the file's line endings were mixed. Fixed (see Section 2).

## 2. What was changed

| File : function | Change | Reason |
|---|---|---|
| `config/message_keywords.json` (**new**) | The editable keyword list: already exists, already registered, already in use, already taken, not available, invalid, try again and similar. A comment explains it. | The one place for message keywords. |
| `executor/run_execution.py`: `_replay_env()` | Passes the config file path (`AUTOFLOW_MESSAGE_KEYWORDS_FILE`). `poll_replay()` also returns `last_retry_until`. | Config location; re-run ranges. |
| `generator/script_generator.py`: `_message_keywords()`, `_message_matches_keyword()` (new) | Loads the config once per run and matches case-insensitively. A missing or broken file means no keywords (nothing pauses), with a warning. **No keyword is written in code.** | Matching. |
| `generator/script_generator.py`: `_fill_label()`, `_fill_field_type()`, `_field_input_label()`, `_is_text_fill()` (new) | Field label (label, placeholder, aria-label, name, id). Field type from `type` email / tel / password, `autocomplete` email / tel / username, else the label words. Box label "Enter new email" / "Enter new phone number" / "Enter new email or phone" / "Enter new value". Only text inputs (no date, checkbox, file, …). | Card contents. |
| `generator/script_generator.py`: `_form_fill_candidates()` (new) | The form's Fill steps: those since the last page change (a Navigate, or a step recorded on another address) up to the submit step, narrowed to the inputs inside the same `<form>` as the submit element when there is one. OTP fields are excluded. | Requirement b). |
| `generator/script_generator.py`: `_identify_field()` (new) | Single-field case: the message's input (aria-invalid / next to the input / id / name) is a recorded Fill step's input, **or** the message names email / phone / mobile / username and exactly one of the form's fields has that type. | Requirement a). |
| `generator/script_generator.py`: `_still_visible_message()` (new) and a read-only `window.__afqaMsgScan()` added to the Phase 4 watcher | After a re-run, a message that simply stayed on screen (it never "appears" again) still counts as the same error. | The re-check. |
| `generator/script_generator.py`: `_StepCursor.rewind_to()` (new) | The step sequence continues from an earlier step, in order. | Re-run from the earliest changed Fill step. |
| `generator/script_generator.py`: end of every step, **before** the Phase 3 fallback card | When a message captured in this step matches a keyword (or, on a re-run, the same message is still shown) and a live log is open, the run pauses with a `field_error` card. Its data: message, source (toast / alert / field error / server response / page message), attempt number, mode single / all, focus step, and fields (label, step, current value with passwords masked, field type, box label). **Continue** applies the typed values to this run and re-runs steps from the earliest changed one through this step, in order. **Retry as is** re-runs this step. **Stop run** marks this step failed and ends the run like a normal failure. No answer: nothing changes. While this card is shown, the fallback card is not shown again. | The pause, re-run and re-check loop. |
| `app.py`: `/api/test/run/start` | Remembers `recording_path` for the run. | Save to recording. |
| `app.py`: `/api/test/run/stream` | Forwards the card data (source, attempt, mode, focus_step, fields, submit_step). `step_retry` now carries the re-run range (`until`). | Card and re-run display. |
| `app.py`: `/api/test/run/pause/answer` and the new `_save_field_values_to_recording()` | Accepts `continue` (with `values`: step → typed value, empty = keep; and `save`) and `retry_as_is`. With **Save to recording**, writes **only** the new `value` of each changed Fill step into the run's recording file. Each step must be one of the open card's fields (matched by token) and still the same Fill step in the file (same action type and timestamp). The file is written atomically, and the result is reported as a plain note on the card. | Save to recording. |
| `templates/live_log.html` | The field-error card in the pinned card: title "The website reported a problem - step N (paused)" plus "- Attempt N" from the 2nd time; the message and its source. **Single-field** layout (label, filled at step K, current value, one EMPTY box) with "Show all fields", or **all fields**. Options "Use for this run only" (default) / "Save to recording". Buttons Continue / Retry as is / Stop run. A light format check marks a wrong value without changing it. Continue with all boxes empty sends Retry as is. A re-run range of lines shows "Running again…" and gets new results. | The card UI. |
| `generator/script_generator.py` (Phase 4 block) | **Defect fix:** the 287 doubled line endings (`\r\r\n`) inserted in Phase 4 were normalised to `\r\n`. The code is otherwise unchanged. | Mixed line endings. |

## 3. MODE A and MODE B

- **Shared:** everything runs in the single replay loop, after any step whose captured message matches a keyword.
- **MODE A:** after Continue, the steps from the earliest changed Fill step through the submit step re-run normally. The run then continues normally to the last step.
- **MODE B:**
  - The same re-run is fast while it is before step N, and normal for step N if N is in the range. Fast mode is decided per step.
  - After success it continues fast to N, runs N normally, then stops.
- **Re-check:** after the re-run, the submit step's capture runs again. Another matching error shows the card again, labelled "Attempt 2", "Attempt 3" and so on.
- **Stop run:** both modes record the submit step as failed and end the run.

## 4. Backup files created (`backups/phase_5/`)

- `backups/phase_5/app.py`
- `backups/phase_5/executor/run_execution.py`
- `backups/phase_5/generator/script_generator.py`
- `backups/phase_5/templates/live_log.html`

New file (no backup): `config/message_keywords.json`.

## 5. Decisions made on my own

1. **"Retry as is" re-runs only the step that showed the message**, with the same values. Nothing was changed, so re-running the Fill steps would type the same values again. **Continue** with changes re-runs from the earliest changed Fill step.
2. **A matching message on a passed step also shows the card.** Keywords like "already exists" usually come with a step that technically succeeded (the click worked).
3. **The card only appears while a live log is open,** and waits at most 180 s (the Phase 3 rules). With no answer the run goes on exactly as before, and the fallback card is not stacked on top.
4. **A missing keyword file disables the pause** (with a warning) rather than falling back to keywords written in code. Keeps "keywords only in the config file".
5. **New values are applied "for this run"** by changing the step's value in the running script only. The recording file is changed only with "Save to recording", and only the `value` field of the changed Fill steps.
6. **Typed values are never logged.** The live log names only the changed fields ("re-running steps 4-7 with new value(s) for Email (step 5)"). The answer file is deleted as soon as it is read.

## 6. Skipped / not possible

- Only **text** inputs are offered, as specified (dates, selects, checkboxes and similar are not).
- Form membership can only be checked when the inputs can be found on the live page. If they cannot, the "since the last page change" rule is used.

## 7. Known limitations

- If a site leaves an old error text on screen after a corrected submit, the re-check may show the card again. Use Retry as is or Continue; Stop always works.
- Field identification by name / id needs the message to be tied to an input (`aria-invalid`, `aria-describedby`, or the same small container) or to name a field type. Otherwise the all-fields card is shown.
- "Save to recording" writes to the recording file that was replayed: an original, or its edited copy. If the recording was changed since the run started (another step at that number), the value is not saved and the card says so.
- A message whose wording matches no keyword never pauses. The normal failure handling, including the fallback card, still applies.

## 8. Manual test checklist

**MODE A**

- [ ] Replay a sign-up that answers "This email is already registered" (toast, alert, field error or JSON 4xx): the live log logs "🔔 Captured …", then shows the card "The website reported a problem - step N (paused)" with the message and its source.
- [ ] Field tied to the email input: a single-field card with label, "filled at step K", current value and an empty box "Enter new email". "Show all fields" switches to all the form's text fields, all boxes empty and passwords masked, with no OTP field listed.
- [ ] Message not tied to a field (for example "Account already exists"): the all-fields card.
- [ ] Type a value without @ in an email box: it is marked, nothing is sent, and the text is not changed. Type a valid new email → Continue: the steps from that Fill step through the submit step run again ("Running again…"), then the run continues normally.
- [ ] Still an error: the card shows "Attempt 2" (then 3, …).
- [ ] Continue with all boxes empty, or Retry as is: only the submit step runs again.
- [ ] Stop run: the submit step is FAILED, the rest NOT RUN, and the status is not PASS.
- [ ] "Save to recording" + Continue: the card says "Saved to the recording (step K)", and the recording file has the new value for that Fill step only (nothing else changed). "Use for this run only": the file is unchanged.
- [ ] Remove `config/message_keywords.json` (or empty the list): messages are only logged, with no card.

**MODE B**

- [ ] ▶ on a step after the failing sign-up: the card appears during the fast steps. After Continue, the re-run steps before N show ⏩ FAST, and the run continues fast to N, runs N normally, then stops.

**Existing flows**

- [ ] Recording, full replay without such messages (no card, same results), Pick Element, validations.
- [ ] The OTP card and the fallback card (Phase 3), the live log and summary, screenshots, the HTML report, the rename popup, and old recordings open and replay.
- [ ] Repeat on Windows and macOS.
