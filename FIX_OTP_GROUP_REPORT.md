# FIX: Split OTP Boxes Filled as One Group

Date: 14 October 2026. Read first: all `*_REPORT.md` files (especially FIX_OTP_GENERIC_REPORT.md and PHASE_3_REPORT.md) and the code.

Inspected:
- run `generated_scripts/screenshoots/session_20261014_173457_20261014_174016/`: `replay_console.txt` and `report.json` (steps 25-28 with their Details text);
- the screenshots `otplogin/step25_verify_with_otp_9_….png` and `otplogin/step26_verify_with_otp_FAILED_17-43-13.png`;
- the recording `storage/recordings/session_20261014_173457.json` (steps 25-28, including the recorded HTML of the boxes).

Nothing was run: no app, no replay, no tests. The checks were static:
- a compile of a generated replay script from the template;
- `node --check` of the box-group page script;
- line-ending checks;
- a read-only comparison of the OTP roles the old and the new detection give for all 81 saved recordings (Section 3).

## 1. Root causes

**Evidence:**

- **Recorded HTML of the OTP row:**
  - box 1: `<input maxlength="4" … type="tel" name="otp0">`;
  - boxes 2-4: `<input maxlength="1" … type="tel" name="otp1|2|3">`;
  - all four sit in one `<div>`, each 30×40 px, in one row.
- **Recorder marks:** steps 26-28 carry the recorder's `otp_field: true` mark; **step 25 (box 1) does not.**
- **Step 25:** a normal fill. Its Details text: "Waiting for the page to finish loading … screenshot". Its screenshot shows "9" (the old recorded digit) in box 1.
- **Step 26:** the OTP card, then failure. Its Details text: "**3 boxes**, OTP has 4 characters, boxes now hold '…'"; "The OTP was typed into **3** separate boxes". The failure screenshot shows box 1 empty and boxes 2-4 filled.

| # | Suspected cause | Verdict |
|---|---|---|
| 1 | OTP detection decided per box | **CONFIRMED.** `generator/script_generator.py → _detect_otp_flow_roles()` takes the **first** step that has OTP signals and only extends **forward** to the other boxes. Box 1 has no signal: <ul><li>`_otp_field_shape()` sees maxlength 4, so it is not a one-character box;</li><li>`_otp_field_standard_signal()` needs a 4-8 digit value, or a one-character box;</li><li>`_looks_like_generic_otp_fill()` finds no rule that fits;</li><li>the name "otp0" is not the whole word "otp";</li><li>the recorder did not mark it.</li></ul> So step 26 (box 2) became the OTP step, and step 25 ran as a normal fill with the stale digit. |
| 2 | The filler starts at the current step's box | **CONFIRMED, by exclusion rather than by starting position.** `_otp_fill_split_boxes()` → `_OTP_ROW_JS` already marks the boxes from the first one. But it only counts inputs with `maxlength="1"`, so box 1 (`maxlength="4"`, a paste box) was **left out of the row**. The row was boxes 2-4 ("3 boxes"), the 4-character OTP did not fit, and its first 3 characters went into boxes 2-4. |
| 3 | The widget cleared or moved boxes after box 1 was filled | **Partly confirmed.** Box 1 held "9" after step 25 and was empty at the failure. The replay never touched box 1 in step 26 (it was not in the row), so **the page itself emptied it**. From the files it cannot be told whether the trigger was editing box 2 or the resend timer running out (it shows "RESEND OTP" at the failure). It did not cause the failure (cause 2 did). The new fill makes it irrelevant: it clears and fills every box, then reads all of them back. When a box does not hold its character it now logs the box **positions** (minimal logging, no values). |
| 4 | Other causes | **Two found:** <ul><li>**The failure Details text printed the boxes' content** ("boxes now hold '…'"), so OTP digits ended up in the report. Fixed: positions only.</li><li>Because box 1 had no OTP role, the field-error card's form fields (`_form_fill_candidates`, which excludes OTP roles) would have offered it as a normal field. It is now an OTP step and excluded.</li></ul> |

## 2. Changes made (`generator/script_generator.py` only)

| Function | Change | Why |
|---|---|---|
| `_detect_otp_flow_roles()` | After finding the first OTP step (the existing rules, unchanged), it also extends **backward** over fill / click steps on boxes of the same group. The **first** box step becomes `otp_fill` and every other box step of the group becomes `otp_fill_more`. Focus clicks are found before the first box (also clicks on any box of the group). Forward extension uses the existing row key **or** the new group rule. Errors give a warning and the existing result. | Tasks 1, 3 |
| new `_otp_box_geom()`, `_otp_row_prefixes()`, `_otp_in_same_group()`, `_otp_group_first()` | Recorded group rule: <ul><li>the existing one-character row (`_otp_group_key`); or</li><li>both steps target a text-like input taking one character (`maxlength=1`, or a very small box: no wider than about 72 px and at most twice as wide as tall), one character per box step;</li><li>on the same page, under the same recorded parent (or the same wrapper level);</li><li>in one row, of similar size.</li></ul> `_otp_group_first()` finds a box step's group step. | Task 1 |
| `_OTP_ROW_JS` (the existing live box-row script) | On the live page the group is the neighbouring inputs that take one character (`maxlength=1`, or very small text fields) in one row and of similar size, looking up to 4 levels above the field. It needs at least 2 maxlength-1 boxes or 3 boxes, and at most 12. Boxes are marked in **DOM order from the first box, whichever box the step targets.** Plain maxlength-1 rows are found exactly as before. | Tasks 1, 2 |
| new `_otp_group_boxes()` | Counts and marks the group. On an error: a warning and 0, so the existing single-field handling is used. | Tasks 1, 4, 7 |
| `_otp_fill_split_boxes()` | Fills the whole group from box 1 (see Section 3). The error text names box positions, never the OTP. | Task 2 |
| `_wait_for_live_otp()` | Optional `message`, used for the length re-ask. The default text and everything else are unchanged. | Task 4 |
| `run()`: the `otp_fill` branch | Logs "OTP group detected (N boxes)", then asks. For split boxes it strips spaces and dashes; a wrong length re-asks the same card. Success logs "OTP filled into all N boxes". | Tasks 2, 4, 7 |
| `run()`: the `otp_fill_more` branch | Never types anything. When the group's step passed: PASS with "Step X: part of the OTP (filled together with step Y)". When it did not: FAILED ("…could not be filled. Nothing was typed here.") instead of a false pass. | Task 3 |
| `run()`: the failure card's Retry | On a later box step of a group: the results from the group's first step onward are removed, and the run rewinds to that step (`_StepCursor.rewind_to`). The OTP is asked again and the whole group is refilled. Retry on the first box step already does this, through `retry_current`. | Task 6 |

Unchanged:
- single-field OTP;
- the OTP card (design, 180 s window, masking, answer files, resume);
- the field-error card / targeted re-run;
- message capture;
- URL / redirect verification and Accept;
- auto-stop;
- Run Until / fast mode;
- `config/message_keywords.json`;
- recording.

## 3. How it works (MODE A and MODE B identical, fast mode included; Windows and macOS)

**Group detection:**
- **Before the run**, from the recording: the first step with OTP signals, plus every recorded box step of the same group before and after it.
- **At the first box step**, on the live page: the box group around the field.
- If any box has OTP signals, all boxes are OTP boxes.
- **Read-only check over all 81 saved recordings:** only `session_20261014_173457` changes (step 25 becomes `otp_fill`; 26-28 become `otp_fill_more`). All other recordings keep exactly their old OTP roles.

**Single ask:**
- At the first box step: "Step X: OTP group detected (N boxes)".
- Then the existing card (masked, Submit / Stop run, 180 s), shown once.

**Length check:**
- Spaces and dashes are removed; nothing else is changed.
- A wrong length is never typed. The card is shown again with "This page expects 4 digits; you entered 5. Enter the OTP again.", and the live log says so too.
- Stop run, or no answer, works exactly as today.

**Whole-group filling:**
- (a) Every box is cleared.
- (b) Each box is clicked in turn and given its own character. Each box is focused explicitly, so a widget that moves the focus by itself cannot cause skipped or doubled characters.
- (c) Every box is read back.
- (d) On a mismatch, every box is cleared and each box is filled directly, then read back again. If it still does not match: "Failed: The OTP boxes did not accept the code as expected." This goes to the existing failure card (Retry step / Stop run).
- Success: "OTP filled into all N boxes".
- The OTP is never logged, stored or saved to the recording.

**Step skipping:**
- Every other box step of the group: "Step X: part of the OTP (filled together with step Y)", PASS, nothing typed.
- If the group was not filled: FAILED, nothing typed. Its Retry refills the whole group from step Y.

**Single input / one fill step:**
- A single OTP field: no group, the existing behaviour exactly (no stripping, no length check).
- One recorded fill step on a page with split boxes: that step fills the whole group (Task 2).

**MODE B:** the OTP step is handled the same in fast mode. With N = a later box step, the group is filled at its first step, the box steps up to N show "part of the OTP", and the run stops after N.

## 4. Backups

- `backups/fix_otp_group/generator/script_generator.py`

## 5. Decisions made on my own

1. **"Very small box" means at most about 72 px wide and at most twice as wide as tall**, or `maxlength=1`. It is generic, and it covers a first box that accepts a pasted code (longer maxlength).
2. **A recorded box step must type at most one character** to join a group. A step that typed the whole code is the single-step case (Task 5).
3. **Group order is DOM order.** This matches left-to-right order on normal pages.
4. **A later box step whose group was not filled is FAILED, not PASS.** It never claims a pass, and nothing is typed.
5. **Retry on a later box step rewinds to the group's first step.** Its results from that step on are reopened (the existing range retry in the live log).
6. **Stripping spaces and dashes applies only to split boxes.** The single-field OTP stays exactly as before.

## 6. Limitations

- **Group size:** a group with more than 12 boxes, or with only two boxes that are not both `maxlength=1`, is not treated as a group (the existing behaviour then applies).
- **Recorded box size:** recordings without a bounding box for a box step fall back to the existing maxlength-1 row rule. The live group fill still starts from box 1.
- **Fill method:** a widget that only accepts a pasted code (no per-box input) may fail both fill passes. Then the failure card with the clear reason is shown.
- **Cause 3:** the exact trigger that emptied box 1 in the failing run cannot be determined from its files.

## 7. Manual test checklist

- [ ] Split OTP boxes recorded one fill step per box: the OTP card appears ONCE, at the first box step. All boxes are filled from box 1 ("OTP filled into all N boxes"). The other box steps show "part of the OTP". MODE A and MODE B.
- [ ] A single OTP input field: unchanged behaviour.
- [ ] An OTP widget that auto-advances focus: no skipped or doubled digits.
- [ ] Entering an OTP of the wrong length (and with spaces / dashes): a clear message, and the OTP can be entered again, or Stop run.
- [ ] Run Until with the target being a later OTP box step.
- [ ] Retry step on an OTP failure (on the first box step and on a later one) asks again and refills the whole group.
- [ ] The sign-up flow with the field-error card, targeted re-run and redirect handling still works.
- [ ] Existing flows unchanged: recording, full replay, Run Until, Pick Element, validations, live logs, screenshots, the rename popup, auto-stop on browser close.
- [ ] Repeat on Windows and macOS.
