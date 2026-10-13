# AutoFlow - OTP / Popup / Field-Change Fix Report

Date: 12 October 2026

## 1. Root causes (written before any code was changed)

### 1.1 Part 1 - which change broke the Sportiza OTP flow

**No code change broke it.** The failing check is the same in every backup.

**Fingerprints.** These code blocks give the same MD5 fingerprint in every backup since the cross-platform change:

- `_MODAL_CONTENT_PAINTED_JS` (the paint check);
- `_wait_for_modal_target_visible._confirmed`;
- the run() "modal-no-navigate-check" block.

The backups checked are:

- `_backup_before_crossplatform/`
- `.bak_20261009`
- `.bak_fullaudit`
- `.bak_macfix`
- `.bak_popupfix`
- `.bak_checkboxlabel`
- the current file

**What changed in between.** Only these functions changed:

- `_compare_post_click`: warning grouping;
- `_detect_otp_flow_roles` / `_looks_like_otp_fill_step`: generic OTP detection was added;
- `_wait_for_live_otp`: an unlink fix.

None of them takes part in the failure at step 12.

**What did change: the recording.**

| Recording | Steps between "Send OTP" and the OTP fill | Result |
|---|---|---|
| `session_20261009_110013`, `20261007_000343` and the other older Sportiza recordings | none | PASS |
| `session_20261012_105745` | two clicks on the OTP field (steps 12 and 13) | FAIL |

**Evidence from the replay logs**

- `…110013_20261009_110051/replay_console.txt` (passing run): after the "Send OTP" click (step 11), no `[modal-no-navigate-check]` line appears. The OTP input is not in the page yet at the moment of the check, so the check is skipped.
- `…105745_20261012_111519/replay_console.txt` (failing run): after the click on the OTP field (step 12), the next target is the same input. That input is already in the page, so the check runs and logs:
  - `TIMEOUT after 6.0s - dom_appeared=True, content_painted=False`;
  - `Failed: Expected a popup to open after clicking 'One-Time Password'…`.

### 1.2 Part 2 - the false "Expected a popup" at step 12

**Root cause.** The popup was already open, and the target input is transparent by design.

**The recording, steps 8-15**

- Step 8 "Continue" opens the Sign-in popup.
- Steps 9-15 are all recorded `in_modal: true` in the same popup container (`popup_container.css_path = body > div:nth-of-type(6) > div > div:nth-of-type(2) > div`, `role=dialog`).
- Steps 12 and 13 click the OTP input, and step 14 fills it. All three use the same `css_path`.

**The OTP input itself**

- Recorded style: `opacity: 0`.
- Recorded HTML: `maxlength="4" autocomplete="sms-otp" inputmode="numeric"`.
- The input is transparent and laid over drawn digit boxes. It was the same in every older Sportiza recording.

**What the replay did**

- After the step 12 click, run() looks at the next step (step 13, same input). It sits in a `role=dialog`, so it calls `_wait_for_modal_target_visible(was_visible_before=True)`.
- `_confirmed()` runs `_is_modal_content_painted` on the input. The input's own opacity is 0, so the result is always `zero-opacity` and the check never confirms.
- After 6 seconds the step fails with "Expected a popup to open", although the popup had been open since step 8.

**The rule that was missing.** A click made inside a popup that was already open, whose next target was already on screen before the click, did not open anything. Nothing new should be expected of it.

**Recorder side**

- `post_click.dialog_open` is "a dialog is open after the click", read from global page state (`_isStrictDialogOpen()` in `recorder/action_capture.js`). It is true for steps 9-13 although only step 8 opened the popup.
- The replay's "a popup must open" check in `_compare_post_click` already excludes clicks made inside a popup (`in_modal`). But the recording does not say whether the dialog was already open before the click.

### 1.3 Part 3 - the OTP prompt never appeared / the recorded OTP was reused

**`session_20261012_105745`**

- Step 14 was correctly detected as `otp_fill`: the report shows `otp_role: otp_fill`.
- Step 12 stopped the replay first (see 1.2), so the prompt was never reached.
- The detector only looks at the step right before the fill when it searches for the "Send OTP" button. Here that step is a click on the OTP field (step 13), so "Send OTP" (step 11) and the phone entry (step 10) got no role. Baseline roles: `{14: otp_fill, 15: verify}`.

**`session_20261012_105400` (four one-digit OTP boxes)**

- No OTP role was detected, so run `…105618` typed the recorded digits `1`, `2`, `3`, `4`. This is the "recorded OTP reused" problem.
- The cause is in `_otp_field_shape`. It treats a box as part of an OTP row only when the box's parent holds at least 3 `maxlength="1"` inputs.
- On this site every box is wrapped in its own `<div>`. The parent holds 1; the grandparent holds the row: 3 or more in the recorded HTML.
- `_otp_group_key` groups the boxes by their parent path, which differs for every box for the same reason.
- The replay's own box finder `_OTP_ROW_JS` already looks up to 3 levels up. Only the detection from the recording was too narrow.

### 1.4 Part 4 - false "This click also filled/changed a field" warnings

The recorder and the replay compute "fields this click changed" with the same comparison: value before vs value after, fields present before only, visible and editable fields only. But they take the snapshots at different moments and use different visibility rules.

**A. Clicking into a field (Date of Birth, `session_20261012_105400` step 9)**

- **Recorder:** the "before" snapshot is taken in the `click` listener (`_schedulePostClickObservation`, called from the click handler). That is after mousedown, when the field already has focus.
- **Replay:** `_post_click_snapshot` is taken before the whole click, before mousedown.
- The field is a MUI date input that writes its format mask into the value on focus.
- The recording therefore saw no change (`fields_changed: []`). The replay saw `'' -> 'MM/DD/YYYY'` and warned, although the next step (step 10) fills the same field.
- The same applies to any input that formats, masks or prefills itself on focus, on any site.

**B. Fields hidden behind a dialog ("Yes, Import my Profile Data", `session_20261009_152733` step 14; also `145915` and `113246`)**

- The click is inside a Radix dialog. The recorded body has `data-aria-hidden="true" aria-hidden="true"` on the page outside the dialog. All 9 form fields are `aria-hidden` before the click.
- The recorder reads "after" as soon as the page is quiet. The dialog is still recorded as open (`dialog_open: true`), so the form is still `aria-hidden`, the fields count as "not a field a person can see", and none are listed.
- The replay reads "after" only once the page has settled. By then the dialog has closed, the fields are visible, and all 9 are reported as "also filled".
- **The rule that was missing:** a field a person could not see or edit before the click (hidden behind a dialog, `aria-hidden`, not displayed) cannot be compared as "changed by this click". Its "before" value was never something a person saw.

**C. Changes explained by the next step**

- The replay reads "after" before the next step runs.
- The recorder stops observing at the user's next interaction (`NEXT_EVENTS`), so the next step's own changes are never recorded.
- A value the click put into exactly the field the next step fills is overwritten by that step, so it cannot change the result.

**Not changed (no proof of a root cause)**

- `session_20261007_144239` step 21 ("Continue with VIJAYARAGAVAN" also changed the T-shirt dropdown): the recording lists 4 changed fields, not the dropdown. The saved profile used in replay may simply carry a T-shirt size now. This may be a real difference, so it stays reported.
- `session_20261007_111714` step 20 (a chat send clears the text area): already handled by the existing `submitted_field_accounted` rule. Later runs of that recording no longer show it.

## 2. Which change caused the regression

**None.** Section 1.1 has the fingerprint evidence.

- The popup and paint check has been the same since before the cross-platform change.
- The Sportiza OTP flow passed only because, in older recordings, nothing came between "Send OTP" and the OTP fill. At that moment the OTP input is not in the page yet, so the check is skipped.
- The new recording `session_20261012_105745` has two clicks on the already-present, transparent OTP input. That is the first time the check met this input.
- The "recorded OTP reused" behaviour comes from the split-box recording `session_20261012_105400`. Its one-digit boxes were never detected by any version.

## 3. Fixes

### 3.1 Changes

Backups made before editing:

- `generator/script_generator.py.bak_otpfix`
- `recorder/action_capture.js.bak_otpfix`
- `recorder/record_session.py.bak_otpfix`

Line numbers are those of the current files. Lines marked "template" are inside `SCRIPT_TEMPLATE`, so they reach every generated script.

| # | File:line | Problem | Root cause | Change |
|---|---|---|---|---|
| F1 | `generator/script_generator.py:13416` (`_same_recorded_popup`, new) and `:26410` (run(), no-navigate check), template | False "Expected a popup" on a click inside an already-open popup (step 12) | The paint check demanded proof that the popup opened, for a click made inside a popup that was open already | The check is skipped when all of these hold: the click and the next step were recorded inside the same popup (same `id` or container path, or none on the next step); the next target was already visible before the click. |
| F2 | `generator/script_generator.py:6698` (`_compare_post_click`), template; `recorder/action_capture.js:4682`, `:4755` | A dialog that was already open was credited to every later click | `post_click.dialog_open` is global state after the click | The recorder now also saves `dialog_open_before`. The "a popup must open" check ignores a dialog that was already open before the click. |
| F3 | `generator/script_generator.py:5094` (`_otp_row_level`, new), `:5124`, `:5170`, template | Split OTP boxes not detected, so the recorded digits were typed | The row was looked for only in the parent; a box wrapped in its own element was missed | The row of 3 or more one-character boxes is looked for up to 3 levels up, as the replay's `_OTP_ROW_JS` already does. The group key uses that same level. |
| F4 | `generator/script_generator.py:5177` (`_otp_same_field_click`, new), `:5221`-`:5244` (`_detect_otp_flow_roles`), template | Clicks on the OTP field before the fill were treated as ordinary clicks, and "Send OTP" was searched for at the wrong step | No such role existed | Clicks on the same OTP field (same `css_path`/`xpath`, or the same box row) right before the fill get the new role `otp_focus`. "Send OTP" and the phone entry are then searched for before those clicks. A fill the recorder marked `otp_field` is always treated as an OTP fill. |
| F5 | `generator/script_generator.py:25638`, `:26414`, `:26683`-`:26690`, template | Clicks on the OTP field could fail the replay | as F4 | An `otp_focus` click gets a live-log line. It expects no popup, page change or field change. If the click itself fails, the step reports a **warning** and the OTP fill step continues; that step still fails if the field is really missing. |
| F6 | `recorder/record_session.py:1803`-`:1819` (stop) | Recordings did not say which fill is an OTP | (requested new optional field) | When a recording is saved, an OTP fill gets `otp_field: true` and the clicks on that field right before it get `otp_focus: true`. This uses the same generator rule (`_template_otp_helpers`), not a second implementation. `generate_script` passes both fields through (`:27790`), and `test_case_has_otp_step` honours `otp_field` (`:27646`). |
| F7 | `generator/script_generator.py:6190`, `:6231`, template; `recorder/action_capture.js:4682`, `:4741` | False "also filled N fields" after closing a dialog ("Import Profile") | The fields were hidden (`aria-hidden`) before the click; the recorder read "after" while they were still hidden, and the replay read it after they appeared | Both sides record which fields a person could not see or edit before the click, and never compare those fields. |
| F8 | `generator/script_generator.py:6714`, `:6231`, template; `recorder/action_capture.js:4741`, `:6820` | False "This click also filled the 'Date of Birth*' field" | The recorder snapshots after the press focused the field, the replay before; a field that masks or prefills itself on focus differs | When the click's own target is a field, that field is not compared on either side: the replay excludes the focused field, the recorder the clicked field, and the recorded focus field is dropped from old recordings' lists. |
| F9 | `generator/script_generator.py:6779`, template | A field the next step fills, changed by this click, was reported | The replay reads the result before the next step; the recorder stops at the next interaction | A live change to exactly the field the next fill/select/type step targets (same tag, and same placeholder, aria-label, accessible name or label) is not reported as unexpected. |

### 3.2 Generic rule per fix, and why it behaves the same on Windows and macOS

- **F1:** A click made inside a popup that was already open, whose next target was already on screen, opened nothing, so nothing new is expected of it.
  - Platform: uses recorded data and Playwright `is_visible()` only.
- **F2:** A popup is credited only to the click it appeared after, not to clicks made while it was already open.
  - Platform: page-side JavaScript, identical in every browser.
- **F3:** A one-character box belongs to an OTP row when a nearby ancestor (up to 3 levels) holds 3 or more such boxes.
  - Platform: string checks on recorded HTML.
- **F4:** Clicks on the OTP field just before typing the OTP only put the cursor there.
  - Platform: compares recorded selectors.
- **F5:** An OTP-field click never decides the result; the OTP fill does.
  - Platform: no platform API involved.
- **F6:** The recorder marks OTP fills with the same rule the replay uses.
  - Platform: pure Python on the saved data.
- **F7:** Only fields a person could see and edit before the click can be "changed by the click".
  - Platform: the same JavaScript check (`_isUserEditableField` / `_USER_FIELD_JS`) in recorder and replay.
- **F8:** The field a click goes into is never "also changed" by that click; its value belongs to its own steps.
  - Platform: DOM `activeElement` / event target.
- **F9:** A change the next step overwrites is not unexpected.
  - Platform: compares recorded names.

### 3.3 Why the fixes are safe

- **Real failures, popups and changes are still reported:**
  - a click that is meant to open a popup, where the target was not on screen before the click, is still verified exactly as before;
  - visible fields that change and are not explained by the next step still warn.
- **Nothing is hardcoded:** no site, selector, text, URL or value.
- **Old recordings:**
  - F1, F3, F4, F5, F7, F8 and F9 work from data every recording since early October already has (`in_modal`, `popup_container`, `dom_context`, `post_click.focus`);
  - with that data missing, every rule falls back to the old behaviour;
  - F2 and F6 add optional fields only.
- **The OTP prompt UI is unchanged:** `_wait_for_live_otp`, the Enter button, the Enter key, the timeout, `_otp_fill_split_boxes` and app.py were not touched.

## 4. Recorder check (Part 5)

The evidence comes from the 65 recordings in `storage/recordings/` and `edited/`.

| Finding | Evidence | Action |
|---|---|---|
| `post_click.dialog_open` is global state, so it is true for every click while a popup is open | `105745` steps 9-13 are all `dialog_open: true`; only step 8 opened the popup | **Fixed** (F2): new `dialog_open_before` |
| `fields_changed` snapshot timing and visibility differ from replay | 1.4 A and B | **Fixed** (F7, F8) |
| OTP fills are not marked | requested | **Fixed** (F6) |
| Fills never carry `popup_container` (108 fills, 0 with one), only `in_modal` | count over all recordings | Not changed: no failure comes from it. F1 accepts a next step without a fingerprint when it is `in_modal`. |
| A recording can hold two OTP flows (`session_20261009_112218` fills 141 and 146) | marking simulation | Not changed: replay handles the first OTP flow, as before. F6 marks both fills `otp_field`, which only matters if replay is later changed to handle more than one flow. |

## 5. All-recordings check

### 5.1 OTP roles before and after, for every recording (65 files)

Computed with the template's own `_detect_otp_flow_roles`.

- 62 recordings: identical roles before and after.
- `session_20261012_105745`:
  - before: `{14: otp_fill, 15: verify}`;
  - after: `{10: phone_entry, 11: send_otp, 12: otp_focus, 13: otp_focus, 14: otp_fill, 15: verify}`.
- `session_20261012_105400` and `edited/session_20261012_105400_edited`:
  - before: none (the recorded digits were typed);
  - after: `{13: otp_fill, 14-16: otp_fill_more, 17: verify}`.
  - Replay now asks for the OTP once and types it into the boxes one by one.
- `session_20261009_110013`, `20261007_000343`, `20261006_225255` and all the other older Sportiza recordings: unchanged, so they behave exactly as in their passing runs.

### 5.2 OTP false positives and misses

**Every numeric fill in every recording.** These fields are **not** detected:

- phone and mobile numbers (10 digits);
- "Enter pincode", "Pincode / Zipcode *" (5-7 digits);
- emergency contact number;
- "Enter number between 50000-99999".

All real OTP fields are detected.

**Synthetic checks: 10 out of 10 correct.**

| Case | Detected as OTP? |
|---|---|
| PIN code (4 digits, numeric) | no |
| age | no |
| amount | no |
| zip (6 digits) | no |
| phone | no |
| `autocomplete=one-time-code` | yes |
| "Verification code" label | yes |
| wrapped row of 6 one-character boxes with "Enter the code we sent" | yes |
| the same row labelled "Card digits" | no |
| 4-digit numeric box under "One-Time Password" | yes |

### 5.3 Popup rule (F1)

- `105745`: true for steps 12→13 and 13→14, so the false failure is gone.
- It is false for the click that opens the popup (8→9).
- For "Send OTP" (11→12) it is true, but the OTP input is not on screen before that click, so the check behaves as before.

### 5.4 Past field-change warnings in all run reports

Predicted from the recorded data; no replay was run.

| Warnings | Recording(s) | Result |
|---|---|---|
| 3 × "Date of Birth*" | `105400_edited` step 9 | removed (F8) |
| 5 × "also filled 9 other fields" | `113246`, `145915`, `152733` step 14 | removed (F7) |
| 1 × chat text area | `111714` step 20 | already handled by the existing rule |
| 1 × T-shirt dropdown | `144239` step 21 | **still reported**: the cause is not proven to be false |

### 5.5 Compile checks

- `py_compile`: `script_generator.py` and `record_session.py` OK.
- `node --check action_capture.js`: OK.
- The template substitutes and compiles: OK.
- No new backslashes or `$` inside the template.
- CRLF is kept in all three files (0 bare LF).
- The `SyntaxWarning`s printed during compile were already in `.bak_otpfix`.
- Generated replay scripts were compiled (not run) for:
  - `105745`;
  - `105400_edited`;
  - `110013`;
  - `152733`;
  - `111714` (not an OTP recording).

## 6. Not fixed (listed, not changed)

- **SUSPECTED: "Send OTP" on a site that pre-renders a transparent OTP input.** If the input were already in the page right after the click, the paint check would reject it as `zero-opacity`. It has not happened in any recording; the input always appears after the click. Changing the paint check is risky, so it is left as is.
- **`session_20261007_144239` step 21:** the T-shirt dropdown warning may be a real difference in the saved profile.
- **`105400_edited` run `105822`:** step 12 "Clicked 'Sign up', but the page did not change" is a different failure, outside these four problems.
- **Second OTP flow in one recording:** replay handles only the first (unchanged; see section 4).

## 7. Test checklist (to run manually)

1. Replay `session_20261012_105745`:
   - steps 12 and 13 PASS, with the live log showing "clicking into the OTP field";
   - step 14 shows the Enter OTP prompt; the Enter button and the Enter key both work;
   - the typed value is used, never `1234`;
   - step 15 Verify passes and the page navigates.
2. Replay `session_20261009_110013` (old Sportiza recording): the same prompt as before, and PASS.
3. Replay `edited/session_20261012_105400_edited`:
   - step 13 prompts for the OTP once;
   - the 4 boxes are filled one character each;
   - steps 14-16 show "already filled";
   - step 9 shows no "Date of Birth" warning.
4. Replay `session_20261009_152733`: step 14 shows no "also filled 9 other fields" warning.
5. Let the OTP prompt time out: the step fails with "No OTP was entered…".
6. Record a new OTP flow, clicking the OTP field before typing:
   - the saved JSON has `otp_field: true` on the fill and `otp_focus: true` on those clicks;
   - click steps have `post_click.dialog_open_before`.
7. Regression replays: a non-OTP recording with a real popup (it must still be verified), a checkbox flow, a late-navigation flow, and one run each on Windows and macOS.

## 8. Rollback

Copy each backup over its file:

```
cp generator/script_generator.py.bak_otpfix generator/script_generator.py
cp recorder/action_capture.js.bak_otpfix recorder/action_capture.js
cp recorder/record_session.py.bak_otpfix recorder/record_session.py
```

On Windows, use `copy /Y` with the same names.

Recordings made after the fix carry only extra optional fields (`otp_field`, `otp_focus`, `post_click.dialog_open_before`). The old code ignores them.
