# FIX: OTP Card Not Appearing (Generic Fix)

Date: 14 October 2026. Phase reports 1-6 and the actual code were read first. Nothing was run; the only checks were static (Python parse, a compile of a generated replay script from the template, `node --check`, a Jinja parse, line-ending checks), plus a functional check of the changed page-verification functions on synthetic addresses (Section 4.1).

## 1. Findings: the OTP path, stage by stage

### (a) How the replay decides an OTP is needed

**`generator/script_generator.py` → `_detect_otp_flow_roles(STEPS)`** runs once at the start of `run()` (`_otp_roles`). It gives the roles `phone_entry`, `send_otp`, `otp_focus`, `otp_fill`, `otp_fill_more` and `verify` from:

- the recorder's `otp_field` / `otp_focus` marks;
- `_looks_like_otp_fill_step` (a short numeric fill after a step naming "otp");
- `_looks_like_generic_otp_fill` (the field's own one-time-code / OTP wording / box row);
- Phase 3's `_otp_field_standard_signal` (autocomplete, inputmode + maxlength, box row, name / label words).

**In `run()`** the OTP branch (`_otp_role == "otp_fill"`) waits up to 8 s for the field to be visible, then calls `_wait_for_live_otp()`.

### (b) How the request is written

- `_wait_for_live_otp()` sets `result["awaiting_otp"]` (legacy) and calls **`_pause_and_ask(kind="otp")`** (Phase 3).
- That writes `result["pause"] = {token, kind: "otp", step_index, message, actions: [submit, stop], since, secret, …}` into `report.json` in the run folder, and marks the step `paused`.
- **The OTP request is NOT gated on the live-log watcher.** Only the Phase 3 fallback card and the Phase 5 field-error card check `_viewer_present()`.

### (c) How Flask and the live log receive it

- `executor/run_execution.py → poll_replay()` reads `pause` from `report.json`.
- `app.py → /api/test/run/stream` (SSE) sends a `pause` event once per card token, and `pause_resolved` when it clears. It suppresses the legacy `otp_needed` when the OTP is a card.
- Every event carries `run_id` (Phase 1).
- `templates/live_log.html` ignores other runs' events and shows the pinned `#pauseCard`: masked input, Submit, Stop run.
- A live log opened later starts a new stream with no card sent yet, so the pending card **is** sent to it.

### (d) How the OTP travels back

- The live log POSTs to `/api/test/run/pause/answer` (`app.py`).
- It writes `pause_answer.json` atomically into the run folder (`os.replace`, with the Phase 6 Windows retry), with `{token, action, value}`.
- `_pause_and_ask()` reads it only if the token matches, deletes it at once, and returns the value. The old `otp_input.txt` (`/api/test/run/otp_submit`) is still accepted.
- The value is never printed or stored.

### (e) How the OTP is filled and the replay resumes

- Back in the OTP branch: the step's value is the live value only (the recorded OTP is never typed).
- `_otp_fill_split_boxes()` types box by box for a row of one-character boxes; otherwise the normal fill runs.
- `otp_fill_more` boxes are marked already filled.
- The loop continues. Fast mode (MODE B) is decided per step, so after the OTP the run goes on fast before N and normal from N.

### (f) What can block the card (checked in the code)

| Condition | Finding |
|---|---|
| **Page / URL verification on the OTP page or the step before it** | **CONFIRMED cause** (see Section 2). A PAGE_MISMATCH fails the step that reaches the OTP page. With stop-on-failure, every later step, including the OTP fill, is "NOT RUN", so `_wait_for_live_otp()` is never called. |
| Gating on "live log open" (Phase 3 / 5) | **Not a cause for OTP.** `_wait_for_live_otp()` → `_pause_and_ask()` has no `_viewer_present()` check (only the fallback and field-error cards have it). Unchanged. |
| Run-ID filtering / stale files | **Not a cause** in this design: each run has its own new run folder, answers are matched by card token, and the live log filters by its own `run_id`. Defensively, leftover answer files are now removed at run start (see Section 3). |
| Live log not rendering the card | The card renders. **A small display defect was confirmed:** when a live log is opened while the run already waits, the stream can deliver the `pause` event before the step's `running` line exists. The card shows, but the step's line said "Running…" instead of "Paused". Fixed. |
| OTP detection not marking the step | **Not a cause:** detection runs on the recorded steps (unchanged by the field-error card), and the roles are computed once per run. |
| Windows / macOS file handling | The answer-file rename retry for Windows was added in Phase 6. Paths are `pathlib`. No other difference found. |

**Relevant points from the phase reports:**

- **Phase 3:** OTP routed through the pause engine; the 180 s window; Stop.
- **Phase 4:** message capture.
- **Phase 5:** the field-error card changes Fill values for the run (`STEPS[k-1]["value"] = new`) and can save them, but **nothing told the page verification about the new values**.
- **Phase 6:** the Windows answer-file retry.

## 2. Confirmed root causes

**R1 (the reported symptom: a value changed in the field-error card).** The page verification `_classify_one_url()` → `_query_matches_user_input()` requires every query value that equals text the user typed in the recording to appear unchanged in the live address.

- That text set is `_user_input_texts()`, **cached once from the recorded values**.
- After the field-error card replaced a typed value (for example a phone number), the site correctly put the **new** value in the OTP page's address, but the check still demanded the **old** one → `"mismatch"`.
- Because the path shape was the same, `_page_mismatch_message()` reported "the page address now has a different id than it had earlier in this run".
- The step failed, the run stopped, the OTP steps were NOT RUN, and the card never appeared.
- A path segment carrying the typed value failed the same way.

**R2 (per-run values that change every run, with no card involved).** The within-run id tracking (`_DYN_ID_FWD` / `_DYN_ID_REV`, `_dyn_allowed`, `_dyn_learn`) only treats a value as an id when `_is_dynamic_url_segment` calls it "generated": a UUID, 5+ digits, hex, or a random-looking token.

- Per-run values such as an **email address**, a **phone number** with `+` or separators, or a **JWT-like dotted token** are not ids under that rule.
- In a **path** segment such a value is compared literally → `"mismatch"` on every run where it differs.

## 3. Changes made

| File : function | Change | Why |
|---|---|---|
| `generator/script_generator.py`: **new** `_register_url_substitution()`, `_subst_url_value()`, `_apply_url_substitutions()` (next to the existing verification helpers) | The run's substitutions (recorded Fill value → value typed in the field-error card) are kept (`_RUN_URL_SUBST`). They are applied to the **expected** address (path segments and query values, raw and URL-encoded, also when the value sits inside a longer value, e.g. after a country code) before comparing. The new value is added to the typed-text set, so the live address must carry it. On any error the address is returned unchanged (existing behaviour) with a warning. | R1 |
| `generator/script_generator.py`: **new** `_is_url_id_value()`, `_url_fill_values()`, `_looks_like_email()`, `_looks_like_phone()`, `_looks_like_jwt()` | Extends the existing id notion **for page verification only**: `_is_dynamic_url_segment(v)`, **or** an email, a phone number (7-15 digits, optional +), a JWT-like dotted token, or a value typed in this recording's own non-OTP Fill steps, or a value substituted in this run. | R2 |
| `generator/script_generator.py`: `_has_dynamic_part`, `_dyn_pairs`, `_dyn_translate`, `_path_matches_with_wildcards`, `_query_matches_with_wildcards`, `_classify_one_url` (query loop) | They use `_is_url_id_value` instead of `_is_dynamic_url_segment`. `_classify_one_url`, `_urls_match_with_wildcards` and `_page_mismatch_message` apply the substitutions to the expected address first. `_dyn_translate` (used when a recorded navigation goes to an address with ids) applies them too. | R1, R2, within the **existing** verification (no second URL check) |
| `generator/script_generator.py`: Phase 5 field-error Continue branch in `run()` | Before applying a typed value, `_register_url_substitution(step, old, new)` is called, **never for an OTP step**. | R1 |
| `generator/script_generator.py`: `run()` right after the run folder is created | Removes a leftover `pause_answer.json`, `pause_answer.json.tmp` or `otp_input.txt` at run start. The Stop request is kept. | Task 3 (stale files) |
| `templates/live_log.html`: the `running` event handler | If the card for this step arrived before its line, the new line shows "Paused - waiting for you". | Task 4 (the paused state is always shown) |

Unchanged by design:

- **OTP detection, filling (split boxes), the 180 s window, masked input, Submit, Stop run, and deleting the answer file after reading.** Section 1 (b) and (f) confirm the OTP request never waited on the watcher, and it still doesn't.
- **The Phase 3 fallback and Phase 5 field-error cards** keep their watcher condition. Only the OTP card was required to be independent of it, and it already was.

## 4. Implementation details

### 4.1 Page verification

1. **Substitution first.** `_classify_url(actual, expected)` → `_classify_one_url` replaces, in the recorded address, every path segment / query value equal to (or containing) a recorded value the user changed in this run with the new value.
2. **The existing comparison** then runs unchanged in structure:
   - host, path shape and static segments must match exactly;
   - query values that are the user's typed text (recorded, or new in this run) must be present;
   - id-like values (the extended notion) on both sides are allowed if consistent with the run's id map;
   - other query differences only warn, as before.
3. **Learning.** An id-like value never seen before in this run is learned (`_dyn_learn` on an accepted page). A value learned earlier must stay consistent (`_dyn_allowed`), exactly as before.

**Functional check** (synthetic addresses, the template's own functions):

| Case | Result |
|---|---|
| Phone changed in the card, not registered | mismatch (the reported failure) |
| Same, registered | match |
| `+91…` encoded variant | match |
| Phone in a path segment | match |
| JWT path token | match |
| UUID | match |
| Email in a path | match |
| A learned id appearing with another value later | **mismatch** |
| Wrong path | **mismatch** |
| Wrong host | **mismatch** |
| Changed static word | **mismatch** |
| A typed search term changed on the live page | **mismatch** |
| `_dyn_translate` of a recorded address with the old phone | gives the new one |

### 4.2 The OTP card

- **Requested:** when the OTP step is reached, always (no watcher check). It is written as `result["pause"]` in the run folder's `report.json`.
- **Shown:** by every live log of this run, including one opened later (a new stream sends the current card). The step line shows "Paused - waiting for you", including when the card event arrives before the line.
- **Answered:** through `/api/test/run/pause/answer` → `pause_answer.json` (token-matched, deleted after reading); the legacy `otp_input.txt` also works.
- **Resumed:** the OTP is filled (split boxes box by box) and the loop continues.
- **MODE A:** continues normally to the last step.
- **MODE B:** the loop continues fast until N (fast mode is decided per step), runs N normally, then stops.
- **Card values in addresses:** with this fix, after a field-error card change, the step reaching the OTP page now passes verification in both modes. The verification is the same code in both modes.

## 5. Backup files created (`backups/fix_otp_generic/`)

- `backups/fix_otp_generic/generator/script_generator.py`
- `backups/fix_otp_generic/templates/live_log.html`

## 6. Decisions made on my own

1. **The extended id notion is used only inside page verification** (the functions listed), not in `_is_dynamic_url_segment` itself. That function is used elsewhere (query cleaning, labels), whose behaviour must not change.
2. **Short numbers (1-4 digits) are still not ids in path segments**, following the existing rule (a page number or year is part of the route). They are covered when they are a value the user typed in the recording.
3. **A substitution also replaces the old value inside a longer value** (4+ characters), so `+<country code><number>` style values follow the new number.
4. **The Stop request file is not cleaned at run start.** The user may legitimately press Stop before the replay's first step.
5. **The OTP card's independence from the watcher** was confirmed in code, not changed (it was never gated).

## 7. Limitations

- A per-run value that is none of the generic shapes (a short code, a plain word, an id with spaces) and was not typed in the recording is still compared literally in a path segment. In a query it only warns, as before.
- If a site puts a **transformed** version of a typed value in the address (hashed, re-formatted beyond a prefix), the substitution cannot match it, and the id rules apply instead.
- A Phase 5 keyword message shown on the OTP page (for example a "try again" countdown in an aria-live region) can still raise the field-error card before the OTP step. That is the configured keyword behaviour, not a blocker of the OTP card. It is not changed.
- The failing run's own files were not available in this project folder. R1 was confirmed by tracing the code with the reported message, and reproduced with the synthetic check.

## 8. Manual test checklist

- [ ] OTP sign-up with the recorded values, MODE A (Replay): the OTP card appears at the OTP step; the step shows "Paused"; Submit → filled → the run continues to the end.
- [ ] The same in MODE B (▶ on a step after the OTP): fast steps → OTP card → Submit → fast to N, N normal, stop.
- [ ] OTP sign-up where the field-error card asks for a new phone / email: type a new one → Continue (both "this run only" and "Save to recording"). The submit step reaching the OTP page passes (no PAGE_MISMATCH) even though its address now carries the new value, and the OTP card appears. Test in MODE A and MODE B.
- [ ] A site whose OTP / verification page address contains a value that changes every run (an id, token, email or phone in the path or query): no PAGE_MISMATCH; the OTP card appears.
- [ ] Open the live log only after the run is already waiting for the OTP: the card appears there, and the step shows "Paused - waiting for you".
- [ ] A normal recording without OTP where a step lands on a really wrong page (different path or host): still FAILS with the page-mismatch message, as before.
- [ ] Existing flows unchanged: recording (rename popup), full replay, Run Until, Pick Element, validations, live logs, timestamped screenshots, the field-error card, the failure card.
- [ ] Repeat on Windows and macOS.
