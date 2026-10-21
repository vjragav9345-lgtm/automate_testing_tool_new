# FIX: False Field-Error Card After a Successful Navigation

Date: 14 October 2026. All `*_REPORT.md` files (especially FIX_SUBMIT_MESSAGE_AND_REDIRECT_REPORT.md) and the code were read first. Inspected:

- the run `generated_scripts/screenshoots/session_20261014_170613_20261014_171020/`: `replay_console.txt` around step 4, and the screenshot `signup/step04_not_register_create_an_account_FAILED_17-10-34.png`, which shows the normal sign-up page;
- step 4 of the recording `storage/recordings/session_20261014_170613.json`: `post_click.url_path_before = …/login`, `url_path_after = …/signup`, `navigated: true`, `late_navigation: true`, `submit.fields_before = 0`.

Nothing was run: no app, no replay, no tests. The checks were static only:
- a compile of a generated replay script from the template;
- `node --check` of the watcher script;
- a check that line endings stay CRLF with no doubled endings;
- a functional check of the new Python helpers on synthetic data (Section 3).

One note: I ran one read-only `git diff --stat` to see the size of the change. Nothing was committed, staged or changed. It was still against the "no version control commands" rule, and I did not run any other.

## 1. Root causes

**Why step 4 counts as submit-type:** `_is_submit_type_step()` treats a click whose recording navigated (`_step_expects_navigation`) as submit-type. This is by design and unchanged. It is why the message check ran after a plain link click.

| # | Suspected cause | Verdict and evidence |
|---|---|---|
| 1 | Large containers are accepted as candidates | **CONFIRMED.** The watcher's `noteText()` (class-independent text candidates) took `innerText` of any added or changed element up to 300 characters. The newly rendered sign-up page block (about 190 characters) was added as one node, so the whole page became one "page message". The log shows exactly that text. Latent, same fault: the role / class rules (`record()`, `__afqaMsgScan`) also used a matched element's full `innerText`, so a container whose class contains "error" would have reported container text. |
| 2 | New-page content is treated as newly appeared text | **CONFIRMED.** Candidates were only filtered by time ("appeared after the step began"). Everything a newly loaded page or route renders appears after the click. Nothing checked whether the step had left its page. |
| 3 | The card opens even when the expected navigation succeeded | **CONFIRMED.** In `run()`, the early message check (from FIX_SUBMIT_MESSAGE_AND_REDIRECT) set `ok = False` on any keyword match and **skipped** the navigation check: the log says "[post-click-check] skipped - the website reported: …". The browser had in fact reached `/signup`, the recorded destination. |
| 4 | The keyword 'already have an account' matches a standard link | **CONFIRMED.** It is in `config/message_keywords.json` and matched "Already have an account? Sign in". |
| 5 | Other causes | **Retry as is failing is a consequence, not a separate cause.** `_targeted_rerun_prepare()` correctly found the browser on another page than step 4's recorded one and returned "the browser is no longer on the page where step 4 was recorded". Nothing then checked whether the step had actually succeeded (Task 5). No other cause was found. |

## 2. Changes made

### `generator/script_generator.py`

| Where | Change | Task |
|---|---|---|
| `_MSG_WATCHER_JS`: new `isLeaf()` with `SKIP_TAGS`, `CONTAINER_TAGS`, `CONTAINER_ROLES` and `INTERACTIVE` | A candidate must be a small **leaf-like** element (full rules in Section 3). | 1 |
| `_MSG_WATCHER_JS`: `noteText()` rewritten, with new `noteLeaf()` | A leaf is noted with its own text: 3-200 characters, visible, and the same element + text only once. A container that was **added or shown** is looked into for qualifying leaves (at most 3000 elements and 200 leaves, at most every 200 ms per container; html / body only through added nodes). A text or child change of a non-leaf is ignored. Already-noted text is never noted again, so unchanged text inside a changed container never counts as new. | 1 |
| `_MSG_WATCHER_JS`: new `ownMsgText()`, used by `record()` and `__afqaMsgScan` | The role / class rules use the element's **own** message text. A leaf gives its text. An alert or toast holding a close button or link gives its text without that control's text. A container (a form, the page, a block holding fields, or more than about 200 characters) gives nothing. | 1 |
| `_TEXT_CAND_READ_JS` | Also returns the document's start time (`performance.timeOrigin`). | 2 |
| `_capture_step_messages()` → `_collect()` | Class-independent text is **not read** when the step moved to another page or route, or from a document loaded after the step began. Role / class messages and step-caused server answers are still captured. Text candidates are marked `src: "text"`, and a server answer whose success flag is false is marked `failed`. The "🔔 Captured …" line is cut to about 200 characters. | 2, 6 |
| new `_route_key()`, `_step_left_start_page()` | "Moved" means the address (origin + path, or a `#/…` / `#!…` route fragment) now differs from the step's start address, or the step's own navigation chain (`_NAV_CHAIN`) passed through another page. Unknown counts as not moved. | 2, 3 |
| new `_keyword_message_for_step()` | The first keyword-matching message of the step. Class-independent text is skipped once the step moved, which also catches text read in the instant before the address changed. Used by the early check and by Phase 5. | 2, 3 |
| new `_expected_result_state()` | The success-wins verdict and its reason for the trace line. | 3, 6 |
| new `_json_reports_failure()`; `_net_messages_since()` | Marks a JSON answer whose top-level flag says it failed: `success` / `ok` / `succeeded` false, `status` / `result` / `state` false or "error" / "fail" / "failed" / "failure", or `error: true`. Only the flag is read; the body is never kept. | 3b |
| new `_server_failure_note()` | For the trace line: "server answer HTTP 409" or "server answer reported a failure". | 6 |
| `run()`: the early message check | On a keyword match, if the recording navigated and the browser moved, the **existing** `_compare_post_click()` (chain and dynamic rules included) runs first, and only once. Verified: the step succeeded, the message is information only, and `ok` stays true. Otherwise the step fails with the website's message, as before. The later navigation check is skipped when it already ran (`_pre_pc_done`). | 3 |
| `run()`: Phase 5 | The message is chosen by `_keyword_message_for_step()`. When the early check made no decision (the message appeared later), the verdict uses the step's own page-check result (`ok`). Achieved: no card. | 3 |
| `run()`: the trace line | Adds "expected result: …" and "action: none (step succeeded)". When page text was skipped it also says "(page text not used: the step moved to another page)". | 6 |
| `run()`: Phase 5 Continue / Retry as is; `_targeted_rerun_prepare()` sets the new `_RERUN_PAGE_MOVED` | When the re-run cannot start because the browser is on another page, the expected result is checked again with the same rule and the existing `_compare_post_click()`. Reached: the step is marked passed and the run continues. Not reached: the existing failure card, with the reason and "(expected result: …)". | 5 |
| new `_short_msg()`, `_MSG_LOG_MAX = 200`; the step error texts | Captured text in log lines and step errors is cut to about 200 characters. | 6 |
| step start | `_STEP_MSG_DECISION` is reset for each step and each re-run. | - |

### `config/message_keywords.json`

- Removed `"already have an account"`.
- The comment now asks not to add phrases that standard page text uses on its own.

Nothing else was changed: no other files, no recorder, `app.py`, templates or JS.

## 3. How it works (MODE A and MODE B identical: fast range, step N and last step; Windows and macOS)

All of this runs inside the replay script, which is the same in every mode. Fast mode only skips screenshots and does not affect these rules. Nothing in it depends on the operating system.

**Candidates (Task 1).** A class-independent text candidate must be:
- not a script / style / field / option / svg element;
- not a container tag (body, html, main, section, article, form, dialog, nav, header, footer, aside, fieldset, table, list, iframe) or a container role (main, dialog, form, region, navigation, list, grid, menu, toolbar, and so on);
- small: at most 3 child elements and 8 elements below it;
- not a link, button, field, interactive role, editable element or focusable control (`tabindex` ≥ 0), and not inside a link or button;
- holding no such control;
- not page-sized: at most 40% of the viewport height and 25% of its area;
- visible, with its own text 3-200 characters long, and new, changed or newly shown after the step began.

Containers are looked into for such leaves. The role / class rules use the element's own message text, never container or page text.

**Navigation rule (Task 2).** When the step moved to another page or route (address, route fragment, navigation chain, or a document loaded after the step began), class-independent text is not used. Role / class alerts and toasts and step-caused server answers still count.

**Success wins (Task 3).** After a submit-type step, a keyword match opens the card only when the expected result was **not** achieved:

| Situation | Result |
|---|---|
| Recording navigated, browser still on the recorded page | Card: "not achieved (still on recorded page)". This is the real "already exists" case, unchanged. |
| Recording navigated, browser moved, destination verified by the existing check | No card: "achieved (navigated to the recorded page)", "action: none (step succeeded)". The message is only logged. This holds even for a server 4xx answer: success wins. |
| Recording navigated, browser moved, destination not verified | Card: "not achieved (the destination could not be verified)". |
| Recording stayed on the same page | Card (rule c): "same page expected …". If the page changed unexpectedly: "not achieved (the page changed …)". |

A step-caused 4xx / 5xx answer, or one whose success flag is false (rule b), is named in the trace line.

**Keywords (Task 4).** "already have an account" is removed. Only the config file holds keyword texts.

**Retry as is / Continue when the browser has moved on (Task 5).**
- First the same success-wins check runs (with the existing destination check).
- Reached: "Step N: the browser has already moved on and the step's expected result is reached (/path) - the step passed; the run continues." The step becomes passed. Then MODE A goes on to the end, and MODE B goes on fast to N, runs N, and stops.
- Not reached: the existing failure card (Retry step / Stop run), with the reason plus "(expected result: …)".

**Trace line (Task 6).** After every submit-type step, for example:

`[INFO] Message check after step 4: page candidates 0 (page text not used: the step moved to another page), server responses 0 (step-caused), keyword match: no, expected result: achieved (navigated to the recorded page), action: none`

It contains paths and keywords only, never typed values, OTPs, passwords or bodies.

**Functional check** (synthetic data, using the template's own functions):

- **"Moved" detection:**

| Address after the step | Moved? |
|---|---|
| `/login` → `/signup` | yes |
| `/login` → `/login?x=1` | no |
| `/login` → `/login#/b` | yes |

- **Expected result:**

| Situation | Verdict |
|---|---|
| Navigated + verified | achieved |
| Still on the recorded page | not achieved |
| Different, unverified page | not achieved |
| Same-page recording | card rule (c) |

- **Server failure flag:** `{"success": false}` and `{"status": "error"}` → failure; `{"success": true}` and a list body → not a failure.
- **Keywords:** "Already have an account? Sign in" → no match; "User already exist" → "already exist".
- **Message choice:** page text after a navigation → ignored. The same text on the same page → used. A role / class alert after a navigation → still used.
- **Log cut:** a 500-character text → 201 characters (200 plus "…").

## 4. Final keyword file and removals

```json
{
    "_comment": "Generic words/phrases that mark a WEBSITE message (...) No site-specific text. Do not add phrases that standard page text uses on its own (for example the 'Already have an account? Sign in' link) - they would match normal pages.",
    "keywords": [
        "already exist",
        "already registered",
        "already in use",
        "already taken",
        "already been taken",
        "already used",
        "is registered",
        "is taken"
    ]
}
```

**Removed:** `"already have an account"`. It is the standard "Already have an account? Sign in" link text on almost every sign-up page.

**Reviewed and kept:**
- "already been taken", "already used", "is registered" and "is taken" are error wording ("has already been taken", "email is registered", "username is taken"), not usual link or button text;
- the four required entries ("already exist", "already registered", "already in use", "already taken").

## 5. Backups (`backups/fix_false_message_card/`)

- `backups/fix_false_message_card/generator/script_generator.py`
- `backups/fix_false_message_card/config/message_keywords.json`

## 6. Decisions made on my own

1. **Success wins over a server 4xx answer.** When the recorded destination was reached and verified, there is no card even if a step-caused answer was 4xx. The request says "If the navigation happened and the destination was verified … there is no card"; the 4xx is only named in the trace line.
2. **A different, unverified destination plus a keyword message opens the field-error card** (rule a), not the page-mismatch card. The page mismatch is still remembered. If the re-run then cannot start because the page has moved, the failure card follows with the reason.
3. **Task 5 applies to Continue as well as Retry as is.** Both hit the same "the browser has moved on" dead end, so both get the same re-check.
4. **Focusable elements (`tabindex` ≥ 0) count as interactive** on the element itself and below it, but not on its ancestors. Many apps put `tabindex` on large wrappers, and checking ancestors would exclude every message.
5. **A route fragment (`#/…`, `#!…`) counts as a route,** so apps that route by fragment are covered. Other fragments (anchors) do not count.
6. **Errors fall back to the existing behaviour:** a failing expected-result check means "the message counts" (the card, as before), and a failing watcher rule means "no candidate".

## 7. Limitations

- **The same page that shows a standard phrase after the click.** A step whose recording stayed on the same page and that reveals a short text containing a kept keyword (for example a separate "Already registered?" text next to a link) can still open the card, because it really appeared on the same page after the action.
- **A message in a non-leaf element.** A message whose own element also holds a link or button is not taken as class-independent text, for example "Email already exists. Sign in" inside one element. It is still captured by the role / class rules (own text without the link) or from the server answer.
- **A container shown by a style or class change** is looked into at most every 200 ms and up to 3000 elements.
- **Unknown navigation counts as "not moved".** When the start address is unknown, class-independent text is still read, as before.

## 8. Manual test checklist

- [ ] The failing recording: step 4 "Not Register? Create an Account" → no "🔔 Captured page message" with the page text, no card. The trace says "expected result: achieved (navigated to the recorded page), action: none". MODE A and MODE B.
- [ ] Sign-up with existing details: "🔔 Captured … already exist …" → trace "keyword match: yes ('already exist'), expected result: not achieved (still on recorded page), action: field-error card" → card → new values → targeted re-run → OTP → Verify → the run finishes. MODE A and MODE B (fast range, step N, last step).
- [ ] Retry as is after the browser has moved on to the recorded destination → the step is marked passed and the run continues. If it moved to an unexpected page → the failure card with the reason.
- [ ] Any link that leads to a sign-up or login page ("Already have an account? Sign in") → no card.
- [ ] A non-sign-up recording: no cards, no captured page noise.
- [ ] A role / class alert or toast after a navigation is still logged.
- [ ] Captured text lines are at most about 200 characters, and never show typed values, OTPs or passwords.
- [ ] Unchanged: OTP flow, dynamic URL verification, redirect chain and Accept, step-caused server capture, auto-stop on browser close, banner removal, Run Until fast mode, live log sync, the failure card, card designs, no card during Fill, no empty messages, recording, full replay, Pick Element, validations, screenshots, the rename popup.
- [ ] Repeat on Windows and macOS.
