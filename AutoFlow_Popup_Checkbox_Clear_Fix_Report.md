# AutoFlow QA – Popup, Checkbox and "Text Not Cleared" Fix Report

## Evidence used

- **Recording:** `storage/recordings/session_20261009_145915.json` (display name **cbe_marathon**, 50 steps, recorded on Mac).
- **Latest run:** `generated_scripts/screenshoots/session_20261009_145915_20261009_150141/`: `report.json`, `replay_console.txt`, and the screenshots for steps 10, 12 and 33.
- **What was done:** nothing was run. I read code, compiled it, inspected the recording and screenshots, and generated (did not run) the replay script for cbe_marathon.

## 1. Root causes

### Issue 1 — Step 10, false "unexpected popup" (13.8 s)

**What the run shows**
- The text+tag finder proposed the correct element: `<div>` at (305,265), 309×50, visible.
- At click time the element actually measured was a **different** one: `{x:305, y:400, width:10, height:0}`. This came from the step 10 Details added in the last fix.
- With no size, the normal click was skipped. The force click failed with "outside of the viewport", and the script click had no effect.

**Cause A — the chosen element was lost (code-proven)**
- The decided element is "pinned" with the attribute `data-afqa-cand="<n>"` (`_pin_candidate`).
- Right after that, the click path calls `_prefer_identity_twin` (for text+tag, href and role matches), which runs `_find_by_accessible_identity`.
- That function **clears every `data-afqa-cand` on the page** and re-marks its own candidates with keys "0", "1", … (script_generator.py ~5910). So the pin was erased, and its key could even match one of the new marks.
- The pinned locator then fell back to the finder's positional `page.locator("div").nth(i)`. While the page was still finishing its render after "Add Runner", that pointed at another div (10×0, below the viewport).
- This is also the likely cause of last time's Mac step 9 failure.

**Cause B — the "popup" was never a popup (code-proven)**
- After any failed click attempt, the replay called `_try_dismiss_overlay`. That function **always** printed "An unexpected popup was in the way" and pressed Escape. It never checked that a popup existed.
- Here nothing covered the target. The recording has `dialog_open: false` before step 10, and there is no dialog in the screenshot.
- **Does the recorder store visible dialogs?** Yes, partly. Each step records `in_modal`, `popup_container`, and `post_click.dialog_open` (whether a dialog was open after the step). So "was a dialog open at this point in the recording" is known from the previous step.

### Issue 2 — Step 12, checkbox "found by its position"

**What the recording stored**
- The control is a `<button type="button" role="checkbox" aria-checked="false" value="on" id="terms">`, with a separate `<label for="terms">I have read and agree to the Terms and Conditions</label>`.
- There is no hidden `<input>`. The visible control **is** the button.

**Cause A — wrong name (proven)**
- The recorded name is `"on"`, which is the button's `value` attribute.
- The recorder's generic `accessibleName()` falls back to `el.value` when an element has no text. The click reused the pre-click snapshot profile built with that generic name, instead of the checkbox-specific `getCheckboxAccessibleName()`, which reads the `label for=` text.

**Why every tier failed on replay (console)**

| Tier | Why it was rejected |
|---|---|
| `id` (#terms, the correct element) | "text mismatch: recorded 'on' … own text ''" |
| `role` | "its name is 'i have read and agree…', but 'on' was recorded" |
| `css_path` | same reason |
| `xpath` | same reason |

Only the last-resort label/row proxy click remained, and it is reported as "found by its position".

**Cause B — wrong recorded state (proven)**
- The recording says `expected_state: false`, but the user's click **checked** the box.
- `_predictedCheckedState` reads the live state when the click lands on the control itself. That is right for a native `<input>`, which toggles before the click event. A `role=checkbox` button only changes `aria-checked` when the site's own handler runs, which is after the recorder's capture-phase listener. So the recorder saved the state *before* the click.

### Issue 3 — Step 33, "text was not cleared"

**What the recorder stored**
- `post_click.submit = {fields_before: 4, field_cleared: true, content_added: true}`.
- Its rule counts a field as cleared when it is no longer in the page **or** its text is empty. During recording the 4 filled fields left the page because the form moved to its next section.

**What replay checks**
- Exactly the same rule (`_SUBMIT_READ_JS`), on the same 4 field nodes captured just before the click.
- The definitions already match. The replay was not reading a stale or hidden copy.
- Replay result: `{cleared: false, added: 0}`. The fields were still on the page with their text, and nothing new appeared.

**Did "Next" advance on replay? No.**
- The step 33 screenshots (before and after the click) show the same section, with the red site message **"BIB number not available."** under "Special BIB Number".
- The value 52224 typed at step 31, which was accepted during recording, is now rejected by the site. That is a change in the site's data (the special BIB number is no longer available), not a tool fault.
- **The step correctly fails.** Only its message was misleading.

### Steps 21 "M" and 28 "Sibling" — "This element had moved"

- **Not the same cause as Issue 1.**
- Both are dropdown options whose recorded `bounding_box` is `{x:0, y:0, width:0, height:0}`. The recorder measured them after the dropdown closed.
- The "moved" check compared the live position against that zero box. A zero box is not a recorded position, so the warning was false.

## 2. Fixes

All fixes are generic and identical on Windows and macOS.

| # | File : line | Problem | Change | Why it is safe on Windows and Mac | Backup |
|---|---|---|---|---|---|
| 1 | generator/script_generator.py : 17020 (`_pin_candidate`) | The pin shared the `data-afqa-cand` attribute with the identity tier, which wipes and re-marks it. | The pin uses its own attribute, `data-afqa-pin`. | Only this function and `_PinnedLocator` use the pin. The identity tier's own marks are untouched. A pinned element now stays the element that was decided and checked. Re-rendered elements still fall back exactly as before. | generator/script_generator.py.bak_popupfix |
| 2 | script_generator.py : 3337–3410 (new `_BLOCKING_POPUP_JS`, `_blocking_popup_over`); 19712 (failed-click path) | Escape was pressed and a "popup" warning given after any failed click. | Escape and the close button are used only when there is a real popup. That means a visible dialog layer (role=dialog/alertdialog, aria-modal, or `<dialog open>`) that does not contain the target, or a visible fixed/absolute layer at least as large as the target over its centre. It must not be the target, its child, its ancestor or its label. It must also persist through a short wait (the existing 3 s fallback timeout, so fades and loading backdrops don't count), and the recording must not have had a dialog open at this point (previous step's `dialog_open`). The target is scrolled into view first. Otherwise nothing is pressed; Details says so, and the click is retried once as before. | The overlay guard before the step and `_close_unexpected_popup` are unchanged, so real popups are still detected and closed there. In this path a real covering popup still gets Escape and the close button exactly as today. | same |
| 3 | script_generator.py : 16730 (`_verified_target_relocation`) | A zero recorded box was compared as if it were a position (steps 21, 28). | A recorded box with zero width and height counts as "no recorded position". | Only affects boxes with no size. The warning still appears for real moves. | same |
| 4 | recorder/action_capture.js : 3833 | Checkbox clicks reused the generic snapshot name (its value, "on"). | For a checkbox, radio or switch, the reused profile gets the label name from `getCheckboxAccessibleName`. | Applies to new recordings only, the same on every OS. Other clicks are unchanged. | recorder/action_capture.js.bak_popupfix |
| 5 | action_capture.js : 3453 (`_predictedCheckedState`) | A role=checkbox/switch/radio control clicked directly recorded its state from before the click. | For a non-native control with `aria-checked`, the after-click state is predicted: checkbox/switch toggles, radio becomes checked. Same as is already done for native inputs clicked through a label. | Native inputs are unchanged. New recordings only. | same |
| 6 | action_capture.js : 3921 | Only the after-click state was stored. | New field `checked_before` (the state before the click) on check steps. | Additive field. | same |
| 7 | action_capture.js : 4478 | "Cleared" didn't say whether the fields were removed or emptied. | New field `fields_removed` (how many filled fields left the page) in `post_click.submit`. | Additive. The `field_cleared` rule is unchanged, so recorder and replay keep the same definition. | same |
| 8 | script_generator.py : 27537, 27588 (`_checkbox_named_by_value_fixed`) | Older recordings name such checkboxes by their value. | When the script is generated, a check step whose recorded name equals the control's own `value` attribute (read from its recorded HTML) gets the recorded label (`near_text`) instead, or no name if there is none. | Only check steps whose name is literally their value attribute. Every other step is returned untouched (verified on cbe_marathon: step 12 now carries "I have read and agree to the Terms and Conditions"). | generator/script_generator.py.bak_popupfix |
| 9 | script_generator.py : 27764, 19224 | Replay accepted any page change as proof the checkbox worked. | `checked_before` is passed into the script. When a step has it (new recordings), the control itself must end in the recorded checked state within the existing wait, or the step fails with "The checkbox didn't end up checked like during recording." | Old recordings lack the field and keep today's check, because their recorded state can be wrong (Cause 2B). | same |
| 10 | script_generator.py : 9769–9825 (`_check_submit_result`, new `_page_error_text`) | The failure said "text was not cleared" when the real problem was a validation error. | The failure message now names the real cause: the page's own error text ([role=alert], an invalid field's described-by message, or a short red text next to a form field), or "the page did not move on (the filled-in fields are still there)" when the fields were meant to leave the page. | Text only. It is read only after the check has already failed, and when the step passes or fails is unchanged. | same |

**Old recordings:** cbe_marathon and all other existing recordings still generate and work. New fields are optional, and missing fields mean today's behaviour.

## 3. Step 33

- **Did "Next" advance on replay? No.** The replay screenshots show the form still on the same section.
- **True cause:** the site shows "BIB number not available." for the Special BIB Number 52224 filled at step 31. The site no longer accepts that value. Steps 28 (Sibling) and 31 were filled correctly, as the screenshot shows.
- **New message** (old recording): "Failed: Clicked 'Next', but the page did not move on. The page shows: 'BIB number not available.'"
- **What to do:** use an available BIB number, or leave that optional field empty, in the recording or the editor.

## 4. Not fixed

1. **Text+tag positional locator.** `_find_by_text_tag` still returns `page.locator(tag).nth(i)`. With fix 1 the pin no longer gets lost, but if a site genuinely re-renders the element, the fallback is still positional. Proposed fix: re-run the finder instead of reusing `nth(i)`. Not done because it changes resolution of every text+tag step.
2. **`state_target_proxy` path.** The label/row proxy click still has no checked-state verification. Proposed fix: run the same check as fix 9 after the proxy click. Not done because proxy clicks are last-resort, and I can't confirm their results on Windows without runs.
3. **Recorder zero box for dropdown options** (steps 21, 28). The recorder measures the option after it closes. Proposed fix: measure on pointerdown. Not done because fix 3 already removes the false warning, and changing the recorder's timing is broader.
4. **"Removed or hidden" as cleared.** Both recorder and replay count *removed* or *emptied* fields as cleared, but not *hidden* ones. They agree, so the check is consistent. Counting hidden ones too would change results for existing recordings and is not proven needed by this evidence.
5. **Red-text heuristic.** `_page_error_text` uses standard alert/aria-invalid markup first, then short red text next to a form field. On an unusual site it may not find the message; the failure then says "the page did not move on". The text is never used to decide pass or fail.

## 5. Test checklist (in order, on Mac and on Windows)

1. **Replay cbe_marathon (old recording).**
   - Step 10: no popup warning, normal click, about 2–3 s.
   - Step 12: passes using the `id` locator, with no "position" warning.
   - Steps 21 and 28: no "moved" warning.
   - Step 33: still fails while the BIB number is unavailable, now with "The page shows: 'BIB number not available.'"
   - With a free BIB number (or the field cleared in the editor), step 33 passes.
2. **Record cbe_marathon fresh and replay it.** In the new JSON, step "terms checkbox" should have `text` = the label text, `expected_state: true` and `checked_before: false`. Clicks that submit should have `post_click.submit.fields_removed`. The replay should pass up to the BIB step.
3. **A site with a real popup** (newsletter, cookie consent or modal that appears unexpectedly): it is still closed, and the warning appears only then.
4. **A site with a hidden-input custom checkbox** (hidden `<input>` plus a styled label or span): record, replay, and confirm it ends checked. Uncheck it in a second recording and confirm the replay fails if the state doesn't change.
5. **A multi-section form with Next buttons:** a correct Next passes. Make one field invalid and check the failure names the site's error message.
6. **Replay several other existing recordings** (Sportzia, Myntra, Amazon, Document360): results unchanged.

## 6. Rollback

Each changed file has a `.bak_popupfix` copy made before its first edit:

| File | Backup |
|---|---|
| `generator/script_generator.py` | `generator/script_generator.py.bak_popupfix` |
| `recorder/action_capture.js` | `recorder/action_capture.js.bak_popupfix` |

On macOS or Linux:
```
cp generator/script_generator.py.bak_popupfix generator/script_generator.py
cp recorder/action_capture.js.bak_popupfix recorder/action_capture.js
```

On Windows:
```
copy /Y generator\script_generator.py.bak_popupfix generator\script_generator.py
copy /Y recorder\action_capture.js.bak_popupfix recorder\action_capture.js
```

Restart the app afterwards. Replay scripts are regenerated on the next save or run.
