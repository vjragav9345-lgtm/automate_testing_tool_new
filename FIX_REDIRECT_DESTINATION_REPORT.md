# FIX: Redirect-Chain Destination Verification, "Accept This Page", Step-Caused Server Messages

Date: 14 October 2026. All `*_REPORT.md` files and the code were read first. Inspected: run `generated_scripts/screenshoots/session_20261014_142715_20261014_162338/` (`report.json`, `replay_console.txt`, the `feed/step18_…FAILED…` screenshots) and recording `storage/recordings/session_20261014_142715.json`. Nothing was run; the only checks were static (Python parse, a compile of a generated replay script from the template, `node --check`, a Jinja parse, line-ending checks), plus a functional check of the new functions on synthetic data (Section 3).

## 1. Root causes

### Step 18 ("Verify") page-mismatch failure

**CONFIRMED - the recorder kept an intermediate address of a redirect chain (suspected cause 1):**

- Recorded step 18: `post_click.url_path_after = "…/"`, `late_navigation: true`, `navigated: true`.
- The recorder's late-navigation watch (`recorder/action_capture.js`, `afqaWatchLateNavigation`) reports every address change after the click.
- But `recorder/record_session.py → _merge_post_click()` drops `url_path_after` from later patches once `navigated` is set. So only the **first** hop (`/`) of the site's `/otp → / → /feed` journey was stored. The recorder was not changed (recording must stay unchanged).

**CONFIRMED - replay compared only the final address:**

- `generator/script_generator.py → _compare_post_click()` judged `_classify_url(live_url, expected, recorded chain)`, with `live_url` = the settled page `/feed`, and failed with `_page_mismatch_message()`: "The recording reached '/', but the browser went to '/feed'".
- The addresses the browser passed through during the step were never looked at.

**Follow-on failure (not a separate cause):** the failure card's Retry re-ran Verify while the browser was already on `/feed`. The target was gone, so the run failed with "The browser is on '/feed', but this step was recorded on '/otp'". This is a consequence, not a cause.

**Account-state redirect (suspected cause 2): cannot be confirmed or excluded from the files.** The run does not show whether the replay itself passed through `/` (this information was never recorded before this fix). The new chain check covers the redirect case. The new "Accept this page and continue" covers a genuinely different landing page.

### "🔔 Captured server response: Route GET:/api/…/unread-count?… not found"

**CONFIRMED (suspected cause 3):**

- `_net_messages_since()` (FIX_SUBMIT_CAPTURE) read every recent fetch / xhr answer that arrived after the step started.
- This 404 came from a request the **newly loaded `/feed` page** made (background polling), not from the Verify action.

**Other causes:** none found.

## 2. Changes made

### `generator/script_generator.py`

| Function / constant | Change | Why |
|---|---|---|
| new `_track_navigations()`, `_NAV_CHAIN`, `_NAV_CHAIN_MARK`, `_step_nav_chain()`; registered on the first replay page, on every new tab (`_on_replay_new_page`) and on a crash-recovery page | Records every **main-frame** address (Playwright's `framenavigated`, which also fires for in-page history changes). The position where each step begins is marked at step start. | Task 1 |
| new `_verify_destination_by_chain_or_recording()`; called in the **existing** `_compare_post_click()` when the final verdict is a mismatch after a real navigation (`kind` recorded / next_navigate / href) | Verified when (1) an address of **this step's chain** matches the recorded destination (the existing `_classify_one_url` rules, including run substitutions and learned ids), or (2) the final page is the page **the recording itself reached next** (the next recorded step's `page_url`, when that is a different page). Logs `[INFO] Passed through the recorded page (/x), then the site redirected to /y. Replay is continuing.` or `[INFO] The site went on from the recorded page (/x) to /y - the page the recording itself reached next…` (paths only). Otherwise the result is unchanged (fails as today). Errors give a warning and the existing result. | Task 1 |
| `_page_mismatch_message()` | Remembers `(expected, actual)` for this step (`_LAST_PAGE_MISMATCH`, reset at each step start). | Task 2 |
| `run()`: the existing failure card (fallback card) | When this step's failure is a page / destination mismatch: a third button **"Accept this page and continue"**, and the card message ends with "Expected page: /x - actual page: /y" (also sent as `expected_path` / `actual_path`). **Accept:** the step becomes **WARNING** ("Warning: Destination accepted by the user: /y instead of /x."), the run continues (`ok = True`, so no stop-on-failure), and `_ACCEPTED_ROUTES[recorded page] = accepted page` for **this run only**. Retry step / Stop run and the no-answer / no-live-log rules are unchanged. | Task 2 |
| `_classify_url()` (the shared comparison) | A page the user accepted for a recorded page earlier in this run counts as that page: later steps verifying against the same recorded route accept it consistently. | Task 2 |
| new `_note_request()` (a request listener, installed by `_msg_capture_install`), `_REQ_START`, `_REQ_KEY_STEPS`, `_CUR_STEP_INDEX`, `_STEP_START_URL`, `_request_caused_by_step()`, `_req_key()`; used in `_net_messages_since()` | A server answer is used only when its request: **started after the step began**; was sent by the **page the step started on** (a page the step navigated to makes its own requests); is **not a static resource** (by file suffix); and its **method + path** (query ignored) was **not already requested during an earlier step** of this run (polling). Unknown details keep the earlier behaviour. Requests are only remembered in the handler; nothing is read there. | Task 3 |

### Other files

| File | Change | Why |
|---|---|---|
| `app.py`: `/api/test/run/pause/answer` | Accepts the answer `accept`. | Task 2 |
| `templates/live_log.html`: the pause card's button list | A new button "Accept this page and continue" (shown only when the card offers it). | Task 2 |

**Unchanged:**
- the recorder;
- the targeted re-run;
- DOM message capture and the submit wait;
- the field-error cards;
- the OTP flow;
- substitutions and learned ids;
- auto-stop;
- the banner removal;
- Run Until / fast mode;
- live log sync;
- the failure card's existing buttons;
- `config/message_keywords.json`.

## 3. How it works (MODE A and MODE B identical, fast mode included)

**Chain verification:**
- During every step, the browser's main-frame addresses are collected.
- If the final page differs from the recorded destination, but the recorded destination is one of the addresses passed during this step (for example `/otp → / → /feed` with `/` recorded), the step is verified, an INFO line names the route passed through and the route landed on, and the run continues.

**Recording-based verification:** if the final page is the page of the next recorded step (the recording itself went there next), the step is verified the same way.

**Everything else** (the recorded page nowhere in the chain, and not the recording's next page) fails exactly as before.

**Accept this page and continue:**
- On a page-mismatch failure, with the live log open (at most 180 s), the card shows the expected and actual paths with Retry step / **Accept this page and continue** / Stop run.
- Accept: the step is WARNING with the accepted-destination reason, and the route is remembered for this run only (never written to the recording).
- Then MODE A continues to the end, and MODE B continues fast to N, runs N normally, and stops. If it was the last step, the run finishes or stops as usual.
- No answer: today's failure handling.

**Step-caused server capture:** only answers to requests the step's action itself caused (started during the step, from the step's page, not static, not seen in earlier steps) are read. DOM capture, keyword matching and the field-error card are unchanged.

**Functional check** (synthetic data, the template's own functions):

- **Chain and recording checks:**

| Case | Result |
|---|---|
| Chain `/otp → / → /feed`, recorded `/` | verified (INFO logged) |
| `/feed` only | not verified |
| `/feed` = the recording's next page | verified |
| `/login` | not verified |

- **Accepted routes:**

| Case | Result |
|---|---|
| Before accepting | mismatch |
| After accepting `/` → `/feed` | match |
| `/login` after that | still a mismatch |

- **Server answers:**

| Request | Counted? |
|---|---|
| A poll from the newly loaded page | ignored |
| A path already requested in earlier steps | ignored |
| A request started before the step | ignored |
| A `.js` file | ignored |
| The step's own POST | kept |

## 4. Backups (`backups/fix_redirect_destination/`)

- `backups/fix_redirect_destination/generator/script_generator.py`
- `backups/fix_redirect_destination/app.py`
- `backups/fix_redirect_destination/templates/live_log.html`

## 5. Decisions made on my own

1. **The recorder was not changed** (recording must stay unchanged), even though it keeps only the first hop of a late redirect. The replay-side chain check covers that case.
2. **Recording-based verification uses the next recorded step's page.** That is the only "where the recording went next" information available. For a last step that is none, so a genuinely different landing page then goes to the failure card with Accept.
3. **Chain verification only applies after a real navigation** (`navigated_away`), and only to the destination check of `_compare_post_click()`, not to "stay on this page" checks.
4. **"Caused by the step" uses the page that sent the request.** A request made by a page the step navigated to is background activity of that new page. This is what excludes the unread-count poll, which was first requested during the same step (so the earlier-step rule alone would not have caught it).
5. **Accept stores origin + path pairs** (`_dest_key`), so query values and ids never matter for the accepted route.

## 6. Limitations

- If the site redirects so fast that the recorded intermediate page never becomes a main-frame address in the replay (a server-side redirect that never commits that address), the chain check cannot see it. Then Accept is offered.
- A submit endpoint that was already called by an **earlier** step of this run (same method and path) is treated as background, and its answer is not read. DOM messages are still captured.
- An accepted route applies only to the same recorded page (origin + path) in this run.

## 7. Manual test checklist

- [ ] Sign-up + OTP with new details → Verify. When the site redirects through the recorded page, the run finishes without a page-mismatch failure (an INFO "Passed through the recorded page …" line). Test in MODE A and MODE B.
- [ ] A login / verify flow on a second website that redirects after login: verified the same way.
- [ ] A landing page that really differs: the failure card shows the expected vs actual path → **Accept this page and continue** → the step is WARNING and the run continues / finishes. Retry step and Stop run still work.
- [ ] A deliberately wrong page in a normal recording still fails.
- [ ] No "Captured server response" lines from background polling. Real submit errors (for example "already exists") are still captured and still open the card.
- [ ] The targeted re-run, the OTP card, auto-stop on browser close.
- [ ] Existing flows unchanged: recording, full replay, Run Until, Pick Element, validations, live logs, screenshots, the rename popup.
- [ ] Repeat on Windows and macOS.
