# AutoFlow QA – Mac Fix, Generic OTP and Plain Warnings

## 1. Overview

**What was wrong**

- **Mac failure (Part A).** At step 9 the element AutoFlow had picked had **no size on the page at the moment of the click**. AutoFlow skipped the normal click and fell back to a JavaScript click (`element.click()`). The site ignored that click, and the step was still reported as passed (with a warning). Step 10 then failed because the race options never appeared.
- **OTP only on Sportzia (Part B).** The "Enter OTP" prompt was triggered by one narrow rule: a fill of 4–8 digits whose *previous* step's text contains "otp". Sites with one box per digit (Coimbatore Marathon) record a single one-digit fill, so the rule never fired.
- **Warnings (Part C).** Many main lines were technical (`validate_text: expected …`, `toggle did not reach …`) or long. Repeated field warnings appeared once per field.

**What changed**

- **A.** A backup click now only counts when the page reacts the way the recording shows. Before the JavaScript click, a real mouse click at the element's visible centre is tried.
- **B.** OTP detection is now generic: the field's own markup, its labels, the page context, and rows of one-digit boxes. Split boxes are typed box by box. The existing live-log prompt, Enter button, Enter key and timeout are reused unchanged.
- **C.** Main lines are now one short plain sentence. Technical text moved, unchanged, into Details. Repeated field warnings are grouped into one line.

**How this was checked:** nothing was run. I read the code and recording data, compiled the files, generated replay scripts from saved recordings (not run), and evaluated the new OTP rule against every saved recording.

## 2. Part A — Windows passes, Mac fails

### Proven facts

Evidence: Mac run `session_20261009_113919_20261009_114019`, recording `session_20261009_113919`.

1. **The step 9 click went through `smart_click`'s fallback branch.** `smart_click` uses a normal click whenever the element has a non-zero bounding box. It only reaches `js_click` when the box is missing or zero-size. The report shows `click mechanism: js_click`.
2. **The box was missing at click time.** The console log for step 9 has no `[CLICK-DIAG]` lines and no BEFORE-CLICK element stack. Both are printed only when the element has a non-zero box. Earlier, the same element had passed the visibility check.
3. **The click had no effect.** The step 9 screenshot and the step 10 FAILED screenshot are identical: "Individual – Pay and Register" is not selected and the race cards never appeared.
4. **The recording shows the click should have had an effect:** `post_click.submit.content_added: true`, meaning new content appeared. Nothing checked this after a backup click, so the failure only showed up at step 10.
5. **Your reading is confirmed.** (1) The JavaScript click did not fire real pointer events, and the site did not react. (2) The fallback was accepted without any effect check.
6. **Not the cause:**
   - Viewport and scale factor. The replay always launches with the recorded viewport (1280×720) and `device_scale_factor` 1 on every OS, so the Retina 2× screen does not apply.
   - Paths with spaces (see A4).
   - OS-specific code. A search found no `sys.platform`, `navigator.platform`, `metaKey` or `ctrlKey` branches in the recorder or replay, apart from the venv interpreter path.

### Most likely reason the box was missing (suspected, logged from now on)

- The text+tag finder returns a **position-based locator**, `page.locator("div").nth(i)`.
- The decided element is pinned with a `data-afqa-cand` mark. If the site re-renders that card after the check, the mark disappears and AutoFlow falls back to `div.nth(i)`.
- That can now point at a different, invisible `<div>`, which has no box. The force click fails, and the JavaScript click "succeeds" on the wrong element.
- Whether the re-render lands inside that window depends on machine timing. Step 9 starts 2.4 s after the page loads. That explains Mac versus Windows on the same flow.
- I cannot prove this without a run. The Windows run `session_20261009_114715` is not on this machine. A new detail line now records the measured box and the force-click error, so the next Mac run will show it directly.

### Fixes

| # | File : line | Problem | Change | Why it is safe on Windows | Backup |
|---|---|---|---|---|---|
| A1 | generator/script_generator.py : 8641 and the force-click `except` | Nothing said why the normal click was skipped. | Details now records "Normal click not used: the element had no size … (measured box …)", plus the force-click error. | Logging only. It is written only on the zero-size fallback path. | generator/script_generator.py.bak_macfix |
| A2a | script_generator.py : 8589–8735 (`smart_click` fallback branch) | A backup click counted as success even when nothing happened. | A new `expect_effect_step` parameter, passed only by the step's own click. When the recording shows the click caused new content, a page change or a new tab, each backup method (force, mouse at centre, JavaScript, recorded position) only counts once the page shows that same change, within `EFFECT_VERIFY_TIMEOUT_S`. If not, the next method is tried. If all fail, the click fails with "The click was sent, but nothing happened on the page". The search then continues with the other locators, which re-find the element from scratch. | Normal-size elements take the unchanged `target.click()` path; nothing new runs before it. Recordings without effect data (older recordings, or clicks that changed nothing) behave exactly as before. Other callers of `smart_click` do not pass the parameter and are unchanged. | same |
| A2b | same branch | No real mouse click was tried before the JavaScript click. | After the force click: scroll into view, wait two frames and re-measure. If the box is now real and stable, and the point is not covered (`_point_is_target`), send a real `page.mouse.click` at the centre. Same coordinates on every OS. | Only runs for the step's own click when the box was zero. A truly zero-size element still has no box, so the old order (JavaScript click, then recorded position) is unchanged. | same |
| A2c | script_generator.py : 8736–8800 | — | New helpers: `_FALLBACK_EFFECT_ARM_JS`, `_FALLBACK_EFFECT_READ_JS`, `_recorded_click_effect`, `_fallback_click_had_effect`. They use the recorder's own `content_added` rule: new nodes with 2 or more characters of text. Address and tab-count changes also count. | Read-only page watchers. | same |
| A2d | script_generator.py : 18825, 19578 | — | The step's main click and the retry after a covering popup now pass `expect_effect_step=step`. "mouse_center" is added to the backup-click warning. | The normal path is unchanged. | same |
| A5 | script_generator.py : 19500 (the `force=True` retry after a "not visible" error, click steps) | Same weakness: a forced click was reported as passed with no effect check. | Same effect check. With no effect, it raises, so the existing recovery continues instead of passing. | Changes the outcome only when the recording shows an effect and none happened. That is exactly the false pass you asked to remove. | same |

### A3 — Recorder on Mac versus Windows

- **No Windows recording of this flow is on this machine.** All five recordings from 9 October are from Mac (user agent "Macintosh"; dsf 1; 1280×720). Older recordings have no environment fields. A side-by-side JSON comparison was therefore not possible.
- **The recorder has no OS-dependent code paths.** The same events (pointer, click, focus, input, change and keys) are captured the same way on every OS.
- **A gap found, but not OS-specific (not fixed, see section 5):** for split OTP boxes, the recording keeps only the **last** box. This is proven by `sibling_index 3 of 4` and value `'6'` in `session_20261009_113919` step 6. The site moves focus to the next box before the typed digit lands, so each earlier box is still empty when it loses focus and is skipped. This happens on Windows too. Part B makes it harmless for OTP: the whole live OTP is typed into all boxes.

### A4 — Paths with spaces (`…/claude 6/`)

No confirmed problem.

- **Subprocesses** are started with an argument list, never a shell.
- **Dashboard and live-log links** use `encodeURIComponent`.
- **Report images** are embedded as data URIs.
- **One unencoded link:** report.html line 458 (`/screenshots/raw?path={{ … }}`) is not URL-encoded. Browsers encode spaces there, so it works. A path containing `#`, `&` or `+` would break it. Listed in section 5, not changed.

## 3. Part B — "Enter OTP" on every website

### Why it only worked on Sportzia

- The prompt, the live-log UI, the `/api/test/run/otp_submit` route and `_wait_for_live_otp` were already generic.
- Only the **detection** was narrow (`_looks_like_otp_fill_step`): a fill of 4–8 digits, and the step right before it must mention "otp".
- Coimbatore Marathon records one fill of **one digit** into the last of 4 boxes, so the rule never fired.

### How detection works now (old rule first, unchanged; then the new generic rule)

The new rule is `_looks_like_generic_otp_fill`, script_generator.py:5053, using `_OTP_WORDS`, `_otp_text_signal` and `_otp_field_shape` at 5010–5051. It applies only to **fill** steps whose value is **1–8 digits**. It fires when one of these is true:

1. The field has `autocomplete="one-time-code"`. This comes from the attributes or the recorded HTML.
2. The field's name, id, placeholder, aria-label or accessible name names a one-time code. Matching is by whole word: otp, passcode, totp, 2fa, mfa, "one time", "verification code", "security code", "enter code", "auth code", "confirmation code", "sms code", "access code". For example, "footprint" never matches.
3. The page context names a one-time code (nearby label or heading, item context, or page address) **and** one of these holds:
   - the field is one of a row of 4 or more one-character boxes (`maxlength="1"`); or
   - its `maxlength` (4–8) equals the code length; or
   - it is a numeric field holding 4–8 digits.

The other boxes of the same row recorded right after it are labelled `otp_fill_more`. The previous click is labelled "Send OTP" only when its text names a code or says "send". The click after the row is labelled "verify".

**Checked against every saved recording:**

| Site | Result |
|---|---|
| Sportzia (4 recordings) | Unchanged |
| Coimbatore Marathon (2 recordings) | Newly detected |
| Coimbatore OTP inside a Townscript recording | Newly detected |
| Townscript `pin_code` field | Not detected (B5) |
| Myntra, Amazon, Document360, ChatGPT, YouTube and others | Not detected (B5) |

### Filling (B3)

- **Single field:** the existing fill path, unchanged. This is what Sportzia uses.
- **Split boxes:** the new `_otp_fill_split_boxes` (5226–5275) runs after the live OTP is entered.
  - It finds the row of one-character boxes around the recorded box.
  - It clicks each box in turn and types its character with the keyboard, so the site's own key and input handlers run.
  - It then checks that every box holds its character.
  - Later recorded fills into the same row are skipped with a note.

### Files changed for Part B

- **generator/script_generator.py:**
  - detection: 5010–5145;
  - split fill: 5226–5275;
  - replay branch: 25411–25428;
  - the run-start check `test_case_has_otp_step`, plus `_template_otp_helpers` at 27379. This check decides the extra OTP wait time. It now loads the **same** helper code from the template, so the two cannot drift apart.

The live-log UI, Enter button, Enter key, timeout, and "no OTP entered" behaviour are unchanged. Only the text of the timeout message was shortened (Part C).

## 4. Part C — Messages changed (before → after)

Technical text that was in the main line moved into Details (`[details]`), word for word.

### Replay engine (generator/script_generator.py)

| Line | Before | After |
|---|---|---|
| 18828 | Warning: The element could not be clicked in the normal way, so a fallback click was used. Continuing. | Warning: The normal click didn't work, so a backup click was used. |
| 26729 | Warning: The recorded element could not be found by its own details, so AutoFlow used a fallback (its position on the page). The test continued. | Warning: Couldn't find this element by its details, so it was found by its position on the page. |
| 6679 (grouped) | One line per field: "Warning: Clicking 'X' also changed the 'Y' field, which did not happen during recording. Continuing." | One line: "Warning: This click also filled 9 other fields (first name, last name, date of birth, …). That didn't happen during recording." With one field: "…also filled the 'Y' field." |
| 6679 (grouped) | One line per field: "Warning: During recording, clicking 'X' changed the 'Y' field, but it did not change this time. Continuing." | One line: "Warning: During recording this click also filled 3 other fields (…), but not this time." |
| 16647 | Warning: Target relocated during replay. Recorded page position: (…); replay page position: (…). The same logical target was verified and clicked. | Warning: This element had moved on the page, but it was checked to be the right one and clicked. (Positions moved to Details.) |
| 17349 | Failed: '5K Walk…' was not on this page this time - the results may have changed since the recording (the whole page was checked after waiting 4 seconds). The replay stopped. | Failed: '5K Walk…' wasn't on the page. The previous step may not have worked. |
| 19099 | toggle did not reach its recorded final state - expected checked=True - … | Failed: The checkbox didn't end up checked like during recording. |
| 19352 | drag did not reach its recorded final value - expected …, got … | Failed: The slider didn't end at the value it had during recording. |
| ~19362 | drag's own value control could no longer be read after the drag, … | Failed: The drag didn't change the page like during recording. |
| ~19372 | drag produced no observable effect - … | Failed: The drag didn't change anything on the page. |
| 24275 | validate_text: expected 'A', got 'B' - checked for 9.0s | Failed: The text was 'B', not 'A'. |
| 24421 | validate_value: expected 'A', got 'B' - checked for … | Failed: The value was 'B', not 'A'. |
| 24367 | validate_visible: element is hidden, expected visible - checked for … | Failed: This element is hidden, but it should be visible. |
| 24462 | validate_enabled: element is disabled, expected enabled - … | Failed: This element is disabled, but it should be enabled. |
| 24557 | validate_checked: checkbox is unchecked, expected checked | Failed: The checkbox is unchecked, but it should be checked. |
| 25411 | no OTP was entered within the wait window - the recorded OTP value is never replayed, … | Failed: No OTP was entered in the live log in time. |
| new | — | Failed: The click was sent, but nothing happened on the page (new content appeared during recording). |
| new | — | Failed: The OTP could not be typed into the boxes. / Failed: The OTP did not fit the boxes on the page. |

### Shared live-log and HTML-report headlines (validation/report_generator.py)

| Before | After |
|---|---|
| Failed: Wanted to click 'X' but a different item is on the page now. The replay stopped. | Failed: 'X' wasn't where it was during recording; something else is there now. |
| Failed: Wanted to use 'X' but it is not on the page now. The replay stopped. | Failed: 'X' wasn't on the page. The previous step may not have worked. |
| Failed: Expected to open '/a' but the browser went to '/b' instead. The replay stopped. | Failed: The browser went to '/b' instead of '/a'. |
| Failed: Something on the page (a popup or menu) was covering 'X'. The replay stopped. | Failed: Something on the page (a popup or menu) was covering 'X'. |
| Failed: Expected 'A', found 'B'. The replay stopped. | Failed: Expected 'A', but found 'B'. |
| Note: The page was opened directly by its address because the click did not open it by itself. | Note: The click didn't open the next page, so it was opened directly by its address. |
| Failed: Expected the page to open after the click, but it only loaded when opened directly … could not be confirmed to be the right page. The replay stopped. | Failed: The click didn't open the next page, and opening it directly couldn't be confirmed as the right page. |
| Warning: The recorded click covered a large area of the page, so the replay may not click exactly the same spot. Continuing. | Warning: The recorded click covered a large area, so it may not hit exactly the same spot. |
| Warning: The page took longer than usual to show the next item. Continuing. | Warning: The next item took longer than usual to appear. |
| Warning: The next item took a long time to appear, so the page may not have finished loading. Continuing. | Warning: The next item took a long time to appear. |
| Failed: 'X' was on the page but never showed up on screen the way it should after the previous step. The replay stopped. | Failed: 'X' was on the page but never became visible. |
| Failed: A popup was expected to open after the click, but its content never appeared. The replay stopped. | Failed: The click should have opened a popup, but it didn't appear. |
| Failed: Hovering did not open the menu that holds 'X'. The replay stopped. | Failed: Hovering didn't open the menu that holds 'X'. |
| Failed: The page could not be scrolled to the same place as in the recording because its content changed. The replay stopped. | Failed: The page couldn't be scrolled to the same place as during recording. |
| Failed: Clicked 'X', but the page did not go where it went during recording. The replay stopped. | Failed: Clicking 'X' didn't open the page it opened during recording. |
| Failed: The browser window was closed while the replay was running. The replay stopped. | Failed: The browser window was closed during the replay. |
| Failed: Expected N items on the page, but found M. The replay stopped. | Failed: Expected N items, but found M. |
| Failed: 'X' is enabled, but it was expected to be disabled. The replay stopped. | Failed: 'X' is enabled, but it should be disabled. |
| Failed: 'X' is disabled, but it was expected to be enabled. The replay stopped. | Failed: 'X' is disabled, but it should be enabled. |
| Failed: A value on the page could not be read as a number. The replay stopped. | Failed: A value on the page couldn't be read as a number. |
| Failed: There was no other tab left to close. The replay stopped. | Failed: There was no other tab to close. |
| Failed: The page address is not the one that was expected. The replay stopped. | Failed: The page address wasn't the expected one. |
| Failed: No saved count with that name exists yet. The replay stopped. | Failed: No count with that name was saved earlier in this test. |
| Warning: The checkbox could not be found directly, so its visible label was clicked instead. The test continued. | Warning: The checkbox couldn't be found directly, so its label was clicked instead. |
| Warning: The recorded item could not be found by its details, so AutoFlow used its position on the page. The test continued. | Warning: Couldn't find this element by its details, so it was found by its position on the page. |
| Warning: The item was hidden, so AutoFlow hovered over its menu to show it. The test continued. | Warning: The item was hidden, so its menu was hovered to show it. |
| Warning: The recorded click position no longer matched, so AutoFlow found the item by its name instead. The test continued. | Warning: The recorded click position had changed, so the item was found by its name instead. |
| Warning: The text of this item changed since the recording. The test continued. | Warning: This item's text changed since the recording. |
| Failed: The drag did not change anything on the page. The replay stopped. | Failed: The drag didn't change anything on the page. |
| Failed: The page took too long to respond at this step. The replay stopped. | Failed: The page took too long to respond. |
| Failed: The browser stopped responding at this step. The replay stopped. | Failed: The browser stopped responding. |
| Failed: Something unexpected stopped this step. The replay stopped. | Failed: Something unexpected stopped this step. |

### Dashboard result (executor/run_execution.py)

| Before | After |
|---|---|
| steps failed: [10]; first failure at step 10 ("5K Walk" element): Failed: …; UI elements missing at steps: [10] | Step 10 ("5K Walk" element) failed: '…' wasn't on the page. The previous step may not have worked.; Elements missing at step(s) 10 |
| replay stopped early - N step(s) never ran | The replay stopped early; N step(s) never ran |
| expected content not found on final page | The expected content wasn't on the final page |
| screenshot did not match baseline | The final screenshot didn't match the saved one |
| product not found: X | Product not found: X |

**Logic was not changed by any rewrite.** Texts that code matches on were kept as they were:
- "Could not find", "hidden", "not hit-testable" and "[content-mismatch]" decide retries;
- the "PAGE_MISMATCH … expected to reach … landed on" text is parsed by report_generator;
- "NOT RUN (stopped after step …)".

## 5. Not fixed (suspected or needs a decision)

1. **Positional text+tag locator (likely root of the missing box).**
   - Problem: `_find_by_text_tag` returns `page.locator(tag).nth(i)`. After a re-render it can point at a different element.
   - Proposed fix: when the pinned mark is lost, re-run the finder instead of reusing `nth(i)`.
   - Not done: it changes how every text+tag step is resolved on every OS.
2. **Recorder misses the earlier boxes of split OTP and PIN rows** (A3, all OS).
   - Proposed fix: commit a box when the site moves focus away after a trusted keystroke, using the typed character.
   - Not done: recorder behaviour change.
3. **Other fallback clicks still have no effect check:**
   - the state-target proxy click,
   - the role/text refresh click,
   - the iframe fallback click,
   - the final click at the recorded position.

   Same pattern as A5. Not done: these are last-resort paths whose results on Windows I can't verify without runs.
4. **report.html line 458:** the screenshot link is not URL-encoded. Spaces are fine; `#`, `&` or `+` in a path would break it. Fix: add `|urlencode`.
5. **Console line "CORE FIX MISSING: fill/select retry logic not found".** It prints on every run (seen in the Mac console) and is a false alarm. The timing wrapper replaces `_resolve_and_act_with_retry`, and the self-check then reads the wrapper's source instead of the real function. Console only, so not part of A–C. It is misleading.
6. **Windows run `session_20261009_114715` is not on this machine.** It could not be compared. Please send its `report.json` and `replay_console.txt` if you want the step 9 paths compared.
7. **Not every message was rewritten.** Messages that were already one plain sentence ("Failed: Clicked 'X', but the page did not change the way it did during recording. The replay stopped.", the chat and popup messages) were left as they are. Rewording them is only cosmetic.

## 6. Test checklist (in this order)

**Mac**
1. Replay `session_20261009_113919`. Then check:
   - Step 9: either a normal click, or a "The normal click didn't work, so a backup click was used." warning that **did** select "Individual – Pay and Register", so the race cards appear.
   - Step 10 passes.
   - If step 9 fails, its Details now show "Normal click not used: … (measured box …)" and which backup methods were tried. Send me that text.
2. Sportzia OTP flow: when the OTP step is reached, the "Enter OTP" box appears. Typing the OTP and pressing the Enter button or the Enter key continues the replay as before. Also let it time out once and check the step fails with "No OTP was entered in the live log in time."
3. OTP on another site:
   - **Split boxes** (Coimbatore Marathon `session_20261009_113919`): the OTP prompt now appears at step 6. Enter the real 4-digit code; all 4 boxes fill and "Verify OTP" passes.
   - **Single box:** use a site with one OTP field (autocomplete `one-time-code`, or a field labelled with OTP or verification code).
4. Non-OTP form (for example a Myntra or Amazon recording, or Townscript's pin-code step): no OTP prompt appears.
5. A form where clicking fills several fields: one grouped warning line, not one per field.

**Windows**

6. Replay several existing Windows recordings that passed before. Same PASS/FAIL results, and the same click mechanism for clicks that worked normally.
7. Repeat steps 2–4 on Windows.
8. Open the HTML report and the dashboard result for a failed run. The main lines are short, and Details still holds the full technical text.

## 7. Rollback

Each changed file has a `.bak_macfix` copy made before its first edit in this task:

| File | Backup |
|---|---|
| `generator/script_generator.py` | `generator/script_generator.py.bak_macfix` |
| `validation/report_generator.py` | `validation/report_generator.py.bak_macfix` |
| `executor/run_execution.py` | `executor/run_execution.py.bak_macfix` |

On macOS or Linux:
```
cp generator/script_generator.py.bak_macfix generator/script_generator.py
cp validation/report_generator.py.bak_macfix validation/report_generator.py
cp executor/run_execution.py.bak_macfix executor/run_execution.py
```

On Windows:
```
copy /Y generator\script_generator.py.bak_macfix generator\script_generator.py
copy /Y validation\report_generator.py.bak_macfix validation\report_generator.py
copy /Y executor\run_execution.py.bak_macfix executor\run_execution.py
```

After restoring, restart the app. Replay scripts are regenerated on the next save or run.
