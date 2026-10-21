# FIX: Targeted Re-run After the Field-Error Card

Date: 14 October 2026. All earlier reports and the code were read first. The failing run's own files were inspected: `generated_scripts/screenshoots/session_20261014_142715_20261014_161312/` (`report.json`, `replay_console.txt`, the `signup/` screenshots) for recording `storage/recordings/session_20261014_142715.json`. Nothing was run; the only checks were static (Python parse, a compile of a generated replay script from the template, `node --check` of the new page script, line-ending checks), plus a functional check of the new helper rules on synthetic steps.

## 1. Root cause of the step 12 failure

**Confirmed cause:** the website's own error message moved the consent control, and the old re-run looked for it again by its recorded **position**.

- Step 12's recorded target is a text-less styled control: `<div tabindex="0" class="css-… r-…"><div …></div></div>`. It has `tag: div`, no role, no text, no attributes, no `state_target`, and its only text is nearby (`near_text`: the consent sentence).
- Its locators are positional only: `css_path …> div:nth-of-type(2) > div:nth-of-type(6) > div > div` and the matching `xpath …/div[6]/div[1]/div[1]`.
- After the first Sign up, the website inserted "User already exist" **above** the consent row. Screenshots `step10_date_of_birth_22_11_2000_….png` and `step12_…_FAILED_16-14-46.png` show the message between the date field and the consent row, with the whole form shifted down.
- The consent control therefore moved to the next sibling position. Every locator tier reported "no match", "closest visible candidates: none", including position_fallback, because of the layout shift. The control itself was plainly visible and **ticked** in both screenshots.
- The old flow (`run()` → Phase 5 Continue → `_step_cursor.rewind_to(_from)`, "re-running steps 6-13") re-executed every intermediate step, including this one.
- **Latent second problem (confirmed by the same screenshots and the old flow):** had step 12 been found, re-clicking it would have **unticked** the consent (it was already ticked), and the Sign up would then have failed differently.

**Suspected causes that were NOT the reason here:**

- **No overlay:** no open popup, date picker or menu is visible in either failure screenshot. The date field only kept focus, with "2000" selected, after its refill. Closing an overlay is still added as a precaution (a), because re-clicking fields can open one on other sites.
- **The step 11 hover warning** was a side effect of re-running intermediate steps; it is avoided by skipping them.

## 2. Changes made (`generator/script_generator.py` only)

| Function | Change | Why |
|---|---|---|
| `run()`, Phase 5 field-error branch (Continue / Retry as is) | The "rewind to the earliest changed Fill step and re-execute every step" code is **replaced** by `_targeted_rerun_prepare(...)` followed by re-running **only the submit step** (`_step_cursor.retry_current()`, its old result removed, `retries` / `last_retry_index` / `last_retry_until` = the submit step, so the live log reopens just that line). If preparation is not possible (g), the existing failure card is shown with the reason. **Retry step** re-runs the submit step, **Stop run** ends the run with that step failed, and **no answer** goes on as before. Browser-closed handling is the same as the other cards. | Required behaviour |
| new `_targeted_rerun_prepare()` | (a)-(e) on the same page: see Section 3. Returns `(True, None)` or `(False, reason)`. Never raises. | Required behaviour |
| new `_close_transient_ui()` + `_TRANSIENT_UI_JS` | (a) Detects an open popup: a visible element with `aria-expanded="true"`, or a visible floating (absolute / fixed) listbox / menu / tree / grid / tooltip. Only then it presses **Escape once**. A focused input / textarea / select is blurred (`element.blur()`). Nothing is clicked and nothing can navigate. | (a) |
| new `_targeted_fill()` | Refills one Fill step through the **normal dispatch**, `_resolve_and_act_with_retry` (same locator tiers and the same fill method per field type, including date fields). | (b), (c) |
| new `_field_current_value()`, `_same_field_value()` | Read a field's live value, and compare it ignoring formatting the field adds itself (separators, spaces, case, e.g. a date mask "22/11/2000" = typed "22112000"). | (c) |
| new `_is_semantic_check_step()`, `_remember_check_state()`, `_STEP_CHECK_STATE`; one call at the end of each successful step | Remembers, **read only** (nothing clicked), the state a checkbox / radio / switch step left right after it ran, using the existing `_resolve_checkbox_state()` (native input, wrapping / `for=` label, ARIA). A step counts as checkbox-like only by its recording: a check step, a native checkbox / radio input, a checkbox / radio / switch role, `aria-checked`, or a label. | (d) |
| `_StepCursor.rewind_to()` | Kept (now unused). | minimal change |

**Unchanged:**
- the first-time execution of every step (apart from the read-only state read of checkbox-like steps, which clicks nothing);
- message capture;
- the cards' designs;
- Attempt N;
- the OTP flow;
- URL verification;
- auto-stop;
- Run Until / fast mode;
- the live log;
- `config/message_keywords.json`.

## 3. How the targeted re-run works

When the user clicks **Continue** (or **Retry as is**) on the field-error card shown after submit step S:

- **(g) First check:** the browser must still be on S's recorded page (the existing `_classify_url`, including the dynamic-value rules). Otherwise the failure card says "the browser is no longer on the page where step S was recorded…".
- **(a)** An open popup / menu / picker is closed with one Escape press (only if one is detected), and a focused field is blurred. Logged: "Re-run: closed an open popup / menu…".
- **For each step from the first of the form's recorded Fill steps up to S-1:**
  - **(b) A changed field** (a value typed in the card): refilled with its own Fill step. Logged "Re-run: step K refilled ('<label>', new value)". If it cannot be found, (g) with the reason.
  - **(c) Another Fill field of the form** (the same set the card uses: same `<form>`, or since the last page change). Its live value is read:
    - the same → not touched ("still holds its value");
    - different (for example the site cleared it) → refilled with this run's value ("refilled ('<label>', the page had changed it)");
    - unreadable → left as it is (logged).
    
    OTP fields are never touched.
  - **(d) A checkbox / radio step** whose state was remembered: if it is in that state, it is **not clicked** ("already in required state"). Otherwise it is clicked once and checked ("restored to its earlier state"). If it is not found or not restorable, (g).
  - **(e) Every other step** (clicks into fields, hovers, focus clicks, and controls that are not recognisably a checkbox, such as a text-less styled tick box): **not executed**. Logged "Re-run: step K skipped (already done on this page)".
- **(f)** Step S runs again through the normal step code: the same submit wait, message capture and Phase 5 check. Another matching message shows the card as "Attempt 2", "Attempt 3", and so on. On success:
  - **MODE A** continues to the last step;
  - **MODE B** continues fast to N, runs N normally and stops. If S is the last step or step N, the run finishes or stops as usual.

**Retry as is:** the same (a), (c), (d), (e), (f), with no field value changed.

**Logging and sync:**
- The live log shows only field labels and step numbers, never typed values (passwords are never shown either).
- The re-run submit step's line is reopened and gets its new result.
- The other steps keep their first-run results, so the step rows and statuses stay in sync.

**Both modes:** everything runs inside the single replay loop. Fast mode is decided per step, so MODE B keeps its fast / normal behaviour after the re-run.

## 4. Backups (`backups/fix_targeted_rerun/`)

- `backups/fix_targeted_rerun/generator/script_generator.py`

## 5. Decisions made on my own

1. **A control is treated as a checkbox only when its recording says so** (check step, checkbox / radio input, role, aria-checked, label). A text-less styled tick box (as here) cannot be recognised generically. In the re-run it is **left exactly as it is** (skipped, not clicked), which keeps the state it had after the first run.
2. **The checkbox state is remembered when the step first runs** (read only, through `_resolve_checkbox_state`), so a box the site itself reset after the error can be restored. Clicking a box is never part of this read.
3. **Escape only when a popup is detected** (aria-expanded, or a floating listbox / menu / grid / tooltip). A page whose form sits in a modal never gets an Escape that could close it while nothing is open.
4. **Value comparison ignores formatting** (only letters and digits compared), so a masked field (dates, phone numbers with separators) is not refilled needlessly.
5. **(g) uses the existing failure card** ("step_failed": Retry step / Stop run) with a plain reason. Retry step runs the submit step again; no answer continues as before.

## 6. Limitations

- **Unrecognisable tick boxes:** a checkbox-like control that the recording cannot identify as one, and that the website itself reset after the error, is not restored (it is skipped as "already done"). Restoring it would need knowing it is a checkbox.
- **Unreadable fields** (no readable value) are left as they are.
- **Steps without side effects that must still be repeated** (for example re-opening a section) are skipped. Only Fill fields of the form, checkbox-like steps and the submit step are acted on.
- **Read cost:** the read-only state read after checkbox-like steps adds one element lookup to those steps in normal runs.

## 7. Manual test checklist

- [ ] Sign-up with existing details → card → a new value for ONE field → Continue. Only that field is refilled; the consent tick stays ticked (never clicked); Sign up is clicked again; the run continues (to the OTP). Test in MODE A and MODE B.
- [ ] The same with new values for several fields, including the date field.
- [ ] A site that clears some fields after the error: those fields are refilled automatically ("the page had changed it"); untouched fields are not refilled.
- [ ] A second "already exists" error → the card shows "Attempt 2".
- [ ] Retry as is → nothing is toggled or retyped (except fields the site cleared), and the submit runs again.
- [ ] The live log shows "Re-run: … refilled", "… still holds its value", "… already in required state / restored", "… skipped (already done on this page)", "closed an open popup" (when one was open), and the submit step's new result, never any typed value.
- [ ] Navigate away / cause a page change before answering the card: the failure card explains the form cannot be corrected on the same page.
- [ ] A normal first-time replay is unchanged (no skipped steps, same speed).
- [ ] The OTP card, auto-stop on browser close, and existing flows: recording, full replay, Run Until, Pick Element, validations, live logs, screenshots, the rename popup.
- [ ] Repeat on Windows and macOS.
