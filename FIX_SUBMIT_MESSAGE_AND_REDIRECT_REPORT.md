# FIX: Submit Message Capture (Regression) and Redirect Verification

Date: 14 October 2026. All `*_REPORT.md` files and the code were read first. Inspected:

- the latest run `generated_scripts/screenshoots/session_20261014_142715_20261014_165519/` (console, report, `signup/step13_sign_up_FAILED_16-55-58.png`);
- the earlier runs `…_161312` and `…_162338` (both logged "🔔 Captured server response: User already exist");
- the recording `storage/recordings/session_20261014_142715.json`.

Nothing was run; the only checks were static (a compile of a generated replay script from the template, `node --check` of the watcher script, line-ending checks), plus a functional check of the corrected request rule on synthetic requests.

## 1. Root causes

### Problem A: no field-error card after "Sign up" (regression)

| Suspected cause | Verdict and evidence |
|---|---|
| 1. The watcher only knows roles / class names | **CONFIRMED.** The screenshot shows "User already exist" as plain red text. The site uses generated utility classes (`css-…`, `r-…`) with no alert role and no error-like class, so `_MSG_WATCHER_JS` → `classify()` never matched it. **No run ever had a page (DOM) capture of it**; only the server answer was captured before. |
| 2. The "requests caused by the step" rule from FIX_REDIRECT_DESTINATION | **CONFIRMED - this caused the regression.** Runs `…_161312` and `…_162338` (before that fix) captured "server response: User already exist"; run `…_165519` (after it) captured nothing, and no `captured_messages` folder was even created. `_request_caused_by_step()` rejected the answer. Ruled out: started before the step (impossible: the click starts the request), a static file (it is an API call), sent from another page (it came from `/signup`). That leaves the rule "the same method + path was already requested during an earlier step". Sign-up forms call the same endpoint while typing (availability checks) and again on submit, so the real submit answer was treated as background. Confirmed by elimination; the new decision trace line now shows the counts directly. |
| 3. The navigation failure wins over the message check | **Partly confirmed (ordering).** The post-click navigation check (`_compare_post_click()`, 5 s wait) ran first and logged "[FAILED] The expected navigation did not complete…". The message capture only ran later. In this run it found nothing (causes 1-2), so the generic failure card appeared. Even with a captured message, the log would first have claimed a navigation failure. |

### Problem B: the last step fails on a redirect

- **Not a current cause:** the failing run (`…_162338`) predates FIX_REDIRECT_DESTINATION.
- **That fix is present and wired in the code:**
  - `_track_navigations()` on every replay page and tab;
  - `_verify_destination_by_chain_or_recording()` inside `_compare_post_click()`;
  - "Accept this page and continue" on page-mismatch cards;
  - `_ACCEPTED_ROUTES` in `_classify_url()`.
- **The background "unread-count" answer** is excluded by its rule "a GET sent by a page the step navigated to". That rule is kept (see Section 2).
- **No change was needed for Problem B.**

## 2. Changes made (`generator/script_generator.py` only)

| Function | Change | Why |
|---|---|---|
| `_MSG_WATCHER_JS` (existing watcher, extended) | New class-independent **text candidates** (hidden `window.__afqaTextCand`). Short visible text (3-300 characters) that is newly added, changes, or becomes visible, **whatever its classes**, is recorded with its time, its explicitly linked input (aria-describedby / aria-errormessage), the input it sits next to (a hint) and whether it is inside a `<form>`. Its computed colour is only a **hint** for the type (red range → "field error", else "page message"). The same element + text is recorded once; hidden or emptied text is forgotten (re-shown text counts again); text is cleaned (no invisible characters). The existing role / class rules are unchanged. | Task 1 |
| `_capture_step_messages()` | After a **submit-type** step, it also reads the text candidates since the step began, and keeps **only** those whose text matches a configured keyword and that the role / class rules did not already capture. Non-matching text is never logged, stored or used. One submit wait per step (flag), so the earlier call (below) and the end-of-step call never wait twice. It counts what it captured (page / server) for the trace line. | Tasks 1, 3, 5 |
| `_request_caused_by_step()` (+ `_REQ_KEY_TIMES` in `_note_request`) | The request must have **started after the step began** (static files are always ignored). **POST / PUT / PATCH / DELETE** started then are **always** the step's own. A **GET** is background only when the same method + path was requested **at least twice before the step began** (polling), or when it was sent by a page the step navigated to. The old "requested in any earlier step" rule is removed. | Task 2 (fixes the regression) |
| `_net_messages_since()` | Counts the step-caused JSON answers read, for the trace line. Reading and keyword rules are unchanged. | Task 5 |
| `run()`: just **before** the existing post-click navigation check | For a submit-type step, the message check (submit wait + page + server capture) runs **first**. If a keyword-matching website message was captured: the step's result becomes "Failed: The website showed '<text>' after '<step>'", the navigation check is skipped, and the existing field-error card follows at the end of the step. The fallback (failure) card is not shown for this step; the existing targeted re-run applies on Continue. Without such a message the navigation check runs exactly as before. | Task 3 |
| `run()`: the Phase 5 decision, plus new `_matching_keyword()` | After every submit-type step, one line: `[INFO] Message check after step N: page candidates X, server responses Y (step-caused), keyword match: yes ('<keyword>') / no, action: field-error card / none`. It contains no typed values, OTPs, passwords or bodies. | Task 5 |

## 3. How it works (MODE A and MODE B identical, fast mode included; the submit step in the fast range, as step N, or as the last step)

**Page capture:** after a submit-type step, a captured page message is either:
- one the existing role / class rules find; or
- any newly shown / changed text on the page that contains a configured keyword (for example red text under the form).

Only keyword-matching text is ever used from the class-independent candidates, so normal page content creates no log lines and no cards.

**Server capture:** a submit's own POST / PUT / PATCH / DELETE answers always count. Only repetitive GETs (requested at least twice before the step), GETs from a page the step navigated to, and static files are ignored.

**Card priority:**
1. Submit step → message check first.
2. If there is a keyword message: "🔔 Captured <type>: <website text>", then the decision line ("… action: field-error card"), then the existing field-error card (single-field or all-fields). The generic failure card is not shown. Continue runs the existing targeted re-run.
3. If there is none: the existing navigation check and failure card, unchanged.

**Redirect chain / Accept** (from FIX_REDIRECT_DESTINATION, verified present):
- a recorded destination found anywhere in the step's navigation chain, or the final page being the recording's next page, is verified, with an INFO line of paths;
- a remaining page mismatch offers "Accept this page and continue" (expected vs actual path; WARNING for this run only);
- a real wrong page still fails.

**Decision trace line:** after every submit-type step, so a miss on a new website can be diagnosed from the live log alone.

**Functional check** (synthetic requests):

| Request | Counted for the step? |
|---|---|
| POST submit to an endpoint that was also called while typing | yes |
| GET requested twice before the step | no (polling) |
| GET requested once before the step | yes |
| GET from the page the step navigated to | no |

Also: `_matching_keyword("User already exist")` = `"already exist"`.

## 4. Backups (`backups/fix_submit_message_redirect/`)

- `backups/fix_submit_message_redirect/generator/script_generator.py`

## 5. Decisions made on my own

1. **Kept the "GET from a page the step navigated to" exclusion.** It is what keeps a new page's polling (the unread-count case) out of the log. It never applies to POST / PUT / PATCH / DELETE.
2. **A keyword message makes the submit step's result that message.** It is never silently a pass. If no live log is open to show the card, the run stops with the website's message as the reason (the existing stop-on-failure). Before, it would have been a navigation failure.
3. **Text candidates are 3-300 characters of visible text,** and are only read after submit-type steps. This keeps the watcher light and prevents noise on other steps.
4. **Problem B needed no new change.** The previous fix covers it; its code was verified in place.

## 6. Limitations

- **A message without a keyword:** a website message that contains none of the configured keywords is not used from the class-independent text. By design: only keywords decide.
- **Text inside a revealed container:** text revealed by showing a large container (whose whole text is over 300 characters) is only caught if its own element changes or is added.
- **Repeated GET submits:** a GET submit whose endpoint was already polled twice before the step is treated as background. Its page message is still captured.

## 7. Manual test checklist

- [ ] Sign-up with existing details → after the Sign up click, a "🔔 Captured …" line (page "field error" and / or "server response") and "[INFO] Message check after step 13: … keyword match: yes ('already exist'), action: field-error card" appear → the **field-error card** appears (not the failure card). Test in MODE A and MODE B (fast range, step N, last step).
- [ ] A second website whose "already exists" message uses different styling (no error class): it is still captured.
- [ ] New values → Continue → targeted re-run → OTP card → Verify → the run finishes without a redirect failure, or "Accept this page and continue" appears when the landing page really differs.
- [ ] No "Captured server response" lines from background polling.
- [ ] A normal non-sign-up recording: no cards, no captured noise; decision lines say "keyword match: no, action: none".
- [ ] A deliberately wrong page still fails.
- [ ] Existing flows unchanged: recording, full replay, Run Until, Pick Element, validations, live logs, screenshots, the rename popup, the OTP card, auto-stop on browser close.
- [ ] Repeat on Windows and macOS.
