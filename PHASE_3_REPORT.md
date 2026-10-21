# Phase 3 Report: Pause Engine + OTP

Date: 14 October 2026. Only Phase 3 was implemented. Nothing was run; the only checks were static (Python parse, a compile of a generated replay script from the template, `node --check`, a Jinja parse), plus a read-only OTP-detection comparison over all saved recordings.

## 1. Step 0 findings relevant to this phase

- **Reused from earlier phases:**
  - Phase 1: run-ID filtering, `state` / `step_ref` on events, with `paused` already in the state list.
  - Phase 2: `_FAST_MODE`, the stop file `stop_request.txt` with `_stop_requested()`, the Stop button and the active-run lock.
- **Existing OTP handling:**
  - Detection: `_detect_otp_flow_roles` (the recorder's `otp_field` / `otp_focus` marks, `_looks_like_otp_fill_step`, `_looks_like_generic_otp_fill`).
  - Filling: the normal fill, or `_otp_fill_split_boxes`, which types box by box (kept).
  - Waiting: `_wait_for_live_otp()` wrote `awaiting_otp` and waited up to 180 s for `run_dir/otp_input.txt`, written by `/api/test/run/otp_submit`. The live log showed a plain prompt on `otp_needed`.
  - The recorded OTP is never typed.
- **Where the design differs from the code:**
  - The replay is a **separate process**, not a Flask thread. So the "thread-safe signal tied to the run ID" is a **file in the run's own folder** (named by the run ID). This is the same mechanism the OTP prompt already used. Flask never touches Playwright.
- **The run time limit:** the executor's watcher killed the replay after a fixed `script_timeout_sec`, so a long pause would have killed a waiting run.
- **What happens on failure today:** the step's result is written with its failure screenshot. With `STOP_ON_FAILURE` (the default) the run stops and the remaining steps are "NOT RUN (stopped after step N failed)". OTP steps are excluded from that stop.

## 2. What was changed

| File : function | Change | Reason |
|---|---|---|
| `generator/script_generator.py`: new `_pause_and_ask()` and `PAUSE_ANSWER_FILE`, `PAUSE_CARD_TIMEOUT_S` (180 s), `_PAUSE_TOTAL` | **The one pause mechanism.** It publishes `result["pause"]` = {token, kind, step, message, actions, since, …}, marks the step `paused` and waits for `run_dir/pause_answer.json` with the same token, or for Stop. It returns the answer, or `None` on timeout. It adds up `paused_total_s`, never prints the value, and is wrapped so any error means "no answer" (existing behaviour). | Generic pause-and-ask. |
| `generator/script_generator.py`: new `_viewer_present()` | True while a live log is open (it refreshes `<report>.alive`). | A fallback card only appears when someone can answer it, so unattended runs keep today's behaviour. |
| `generator/script_generator.py`: `_wait_for_live_otp()` | The OTP wait is now an `otp` card: a masked input, Submit and Stop run. The old `otp_input.txt` channel is still accepted. Logs, the 180 s limit and the return value are the same as before. | The existing OTP handling routed through the engine. |
| `generator/script_generator.py`: new `_StepCursor`; the main loop uses `for i, step in _step_cursor` | Like `enumerate(STEPS, 1)`, plus `retry_current()`. | Retry re-runs the same step in order; nothing is skipped or reordered. |
| `generator/script_generator.py`: end of each step, before the existing failure handling | **The fallback card**: a failed step (any type, MODE A and B) pauses with its readable reason and failure screenshot, offering **Retry step** and **Stop run**. Retry removes that failed result and runs the step again. Stop ends the run with that step failed (the remaining steps are "NOT RUN (stopped after step N failed)"). No answer, or no live log, falls through to the existing handling (Phase 2's "Could not reach step N…" in MODE B, stop-on-failure in MODE A). | Requirement. |
| `generator/script_generator.py`: new `_otp_field_standard_signal()` (used by `_detect_otp_flow_roles`) | OTP detection step (2), from the field's own standards: `autocomplete="one-time-code"`; `inputmode="numeric"` with maxlength 4-8; a row of one-character boxes; or its own name / id / placeholder / label containing otp, code, verification, verify, passcode or pin. It needs a value of 4-8 digits (or 1 digit in a box row). A field naming another kind of code (zip, postal, pincode, promo, coupon, card, cvv…) is excluded. | Requirement. It is placed outside the helper range the recorder uses, so recording is unchanged. |
| `executor/run_execution.py`: new `_paused_seconds()`, `_communicate_excluding_pauses()`; `_watch_replay()` | The run's time limit is extended by the time spent paused. `poll_replay()` now also returns `pause`, `retries` and `last_retry_index`. | Pause time never counts toward a time limit. |
| `app.py`: `/api/test/run/stream` | Refreshes `<report>.alive` about once a second. Sends `pause` (card data, `state: paused`) and `pause_resolved`, and `step_retry` (the retried step's line is reopened and resent). It does not send the old `otp_needed` when the OTP is shown as a card. | Live-log delivery. |
| `app.py`: new `/api/test/run/pause/answer` | Writes the answer {token, action submit / retry / stop, value} atomically into the run folder. `stop` also writes the stop request. The value is never logged. | The user's answer. |
| `templates/live_log.html` | A **pinned card** above the log (sticky, never scrolls away; light dialog look like the editor's Pick Element dialog): title "OTP needed / Step failed - step N (paused)", message, failure-screenshot link, a masked input for OTP (Enter submits), and the buttons Submit / Retry step / Stop run. The step line shows "Paused - waiting for you"; on retry it shows "Retrying…" and then its new result. | The card UI. |

The old `/api/test/run/otp_submit` route and `#otpPrompt` are kept, so a script generated before this change still works.

## 3. MODE A and MODE B

All of it lives in the single replay loop, so both modes behave identically:

- **OTP:**
  - The card appears when the OTP step is reached.
  - After Submit, MODE A continues normally to the end.
  - MODE B continues in fast mode until step N (fast mode is decided per step, so it simply goes on).
- **Fallback card:**
  - It shows on any failure, in both modes.
  - Retry re-runs that step in its own mode (fast before N in MODE B, normal otherwise).
  - Stop ends the run with that step failed.
  - If the card is not answered (180 s) or no live log is open, MODE B shows "Could not reach step N: step X failed" and MODE A uses today's stop-on-failure.
- **Stop run** on any card or the Phase 2 Stop button ends the run.
- **Pause time** is excluded from the run time limit in both modes.

## 4. Backup files created (`backups/phase_3/`)

- `backups/phase_3/app.py`
- `backups/phase_3/executor/run_execution.py`
- `backups/phase_3/generator/script_generator.py`
- `backups/phase_3/templates/live_log.html`

## 5. Decisions made on my own

1. **A file signal in the run folder instead of `threading.Event`**: the replay is a separate process (Section 1). The answer is matched by the card's token, so a stale answer can never resume a different pause.
2. **The fallback card only appears when a live log is open** (heartbeat file), and it waits at most 180 s (the same as the OTP prompt). Unattended runs behave exactly as before; no run can hang forever.
3. **Retry replaces the failed result** with the new one, so the report holds one result per step. The live log keeps the earlier failure detail above it as history.
4. **The OTP card's input is masked** (password field). The value only passes through `pause_answer.json`, which is deleted the moment it is read, as the old `otp_input.txt` was. It is never printed, logged or stored in reports.
5. **"code", "verify" and "pin" have an exclusion list** (zip, postal, pincode, promo, coupon, voucher, discount, referral, invite, gift, country, area, dial, tracking, order, product, sku, card, cvv, cvc). These are generic words, not site texts. Without them, ordinary fields like "Zip code" or a card PIN would be treated as OTPs.
6. **The new OTP rule is not part of the recorder's helper range**, so recording output (the `otp_field` marks) is unchanged.

## 6. Skipped / not possible

- **A pause cannot interrupt an action in progress.** Cards appear at step boundaries: when the OTP step is reached, or after a step failed.
- **The OTP prompt's own 180 s window is unchanged** (existing behaviour). It does not count toward the run's time limit.

## 7. Known limitations

- If the live log window is closed, the fallback card is not shown, and today's failure behaviour applies. The OTP card still waits, and can also be answered through the old prompt route.
- A retried step's earlier screenshots and lines stay in the run folder and log as history.
- The "row of 4-8 one-character boxes" check uses the recorded HTML of the box's nearest ancestors. A row made of 3 boxes also counts (the existing split-box rule).
- **All-recordings check (read-only):** the new detection changes the OTP roles of **0 of the saved recordings**. The existing rules already caught every OTP field there, and the new rule adds no false positives.

## 8. Manual test checklist

**MODE A (full replay)**

- [ ] A recording with an OTP step: the live log shows the pinned card "OTP needed - step N (paused)" with a masked input. The step line says "Paused - waiting for you". Submit (or Enter) continues normally to the end. The OTP never appears in the log or report.
- [ ] OTP card → Stop run: the run ends, the remaining steps are NOT RUN, and the status is not PASS.
- [ ] Make a step fail (for example a wrong selector) with the live log open: the card "Step failed - step N" shows the reason, "View failure screenshot", Retry step and Stop run.
  - Retry: the step runs again ("Retrying…") and gets its new result.
  - Stop run: the run ends with that step FAILED and the rest NOT RUN.
- [ ] The same failure with the live log window closed: no card; the run stops as before.
- [ ] Leave the card unanswered for 3 minutes: the normal failure handling continues.
- [ ] A long pause (several minutes) does not make the run "take too long and stop".

**MODE B (▶ Run until step N)**

- [ ] An OTP step before N: the card appears; after Submit, the remaining steps before N run as ⏩ FAST, step N runs normally, then the run stops.
- [ ] A step before N fails with the live log open: the fallback card appears. Retry re-runs it fast; Stop ends the run.
- [ ] No answer: "Could not reach step N: step X failed".

**Existing flows**

- [ ] Recording (start, stop, the rename popup); old recordings open and replay.
- [ ] Pick Element and validations.
- [ ] The live log lines, colours and summary; timestamped screenshots; the HTML report.
- [ ] Split OTP boxes are still filled box by box.
- [ ] A recording without OTP or failures runs exactly as before (no cards).
- [ ] Repeat on Windows and macOS.
