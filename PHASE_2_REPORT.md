# Phase 2 Report: Run Until Selected Step (MODE B)

Date: 14 October 2026. Only Phase 2 was implemented. Nothing was run; the only checks were static (Python parse, a compile of a generated replay script from the template, `node --check` on every changed script, a Jinja parse of the changed templates).

## 1. Step 0 findings relevant to this phase

- **Phase 1** (`PHASE_1_REPORT.md`) is reused unchanged:
  - `run_id` on every live-log event;
  - `state` and `step_ref` on step events, with the `fast` state already in the vocabulary;
  - the real running row on the dashboard;
  - the failure screenshot link.
- **One replay path:**
  - `/api/test/run/start` → `generate_script()` → `executor.start_replay()` → a **separate process** running the generated script's `run()` loop.
  - Options reach that process through environment variables (the existing `AUTOFLOW_LIVE_ACK` is passed this way). MODE B uses the same mechanism, so it is an option of the same path, not a second engine.
- **Delays:** recorded pacing is **never** replayed as a sleep. There are no artificial delays to remove. The only waits are technical ones (page load, element readiness, settle), and those are kept.
- **Screenshots:**
  - per-step screenshots go through `_capture_screenshot()`;
  - failure screenshots through a separate `_capture_failure_screenshot()`;
  - explicit Screenshot *actions* through `_capture_screenshot_when_settled()`.
- **Where the step list is:**
  - The Recording Editor's step rows (`renderActions()` in `templates/recording_editor.html`) are the only per-step list a user can act on, so the ▶ icon goes there.
  - The dashboard's Replay button lives on each recording card (`static/js/script.js`).
- **Full-run results:**
  - The editor's health badges and the dashboard's "View Last Log" read `/api/recordings/last_result`, which picked the newest run folder of a recording.
  - The dashboard also keeps an in-memory cache, filled only by its own full replays.
- **Stopping a run:** there was no Stop. The replay is a separate process, so Flask must never touch its browser. Stop therefore uses a file in the run folder, the same cross-process hand-off the existing OTP prompt uses (`otp_input.txt`). There is no `threading.Event` here, because there is no shared thread.
- **Browser after a run:** the script itself closes the browser after its 5-second hold. A partial run ends through the same code, so it is handled exactly the same.

## 2. What was changed

| File : function | Change | Reason |
|---|---|---|
| `generator/script_generator.py`: new `_FAST_MODE`, `_run_until_step()`, `_stop_requested()` | MODE B switch from `AUTOFLOW_RUN_UNTIL_STEP=N`, and the Stop-file check. | One option of the existing path. |
| `generator/script_generator.py`: `_capture_screenshot()` | Returns nothing while `_FAST_MODE` is on. Failure screenshots and Screenshot actions are unaffected. | Fast mode drops per-step screenshots only. |
| `generator/script_generator.py`: `run()` before the loop | For MODE B: `result["partial_run"] = {"until_step": N}`, `recorded_steps` / `total_steps` = N, and the live-log line "Partial run (until step N): steps 1-(N-1) run quickly…". | Label and step count of a partial run. |
| `generator/script_generator.py`: top of each step | `i > N` → stop. Fast mode is on for `i < N`. The Stop file → "Run stopped by the user before step i." | Stop after step N fully completed (its screenshot and waits included); Stop button. |
| `generator/script_generator.py`: step results (normal and crash) | `"fast": true/false`. | Fast steps are shown as fast. |
| `generator/script_generator.py`: end of a step | A fast step that failed → "Could not reach step N: step X failed - <reason>". The run stops; the step's own failure screenshot and reason are in its result. | The requirement for a failure before N. |
| `generator/script_generator.py`: after the loop | "Stopped after step N (partial run)." Steps after N are not part of the run (never backfilled). User-stopped steps read "NOT RUN (the run was stopped by the user)". | The partial-run end and summary. |
| `generator/script_generator.py`: `_wait_for_live_otp()` | The Stop file ends the OTP wait. | Stop also works during an OTP prompt. |
| `executor/run_execution.py`: `start_replay(…, run_until_step=None)`, new `_replay_env()`, new `active_run_ids()` | Passes N only for MODE B (an inherited value is removed). Lists runs in progress. `partial_run` / `stopped_by_user` are carried into the final result. A stopped run is never PASS. | Plumbing; "a run is active". |
| `app.py`: `/api/test/run/start` | Optional `run_until_step` (validated 1..steps) and `step_check`: step N's action type and timestamp must match the **saved** step N, otherwise "Save the recording first". The step count and meta use N. | The editor's step N is the run's step N. |
| `app.py`: new `/api/test/run/stop`, `/api/test/run/active` | Stop writes `stop_request.txt` in the run folder. Active lists the running runs. | The Stop button; disabling buttons while a run is active. |
| `app.py`: `_step_display_status`, `_DISPLAY_TO_STATE` | A passed fast step has status / state `fast`. | The live log shows it as fast. |
| `app.py`: stream `meta` / `summary` | `partial_until`. The summary sentence starts "Partial run (until step N): stopped after step N." / "…could not reach step N - step X failed." / "…stopped by the user." | Labels. |
| `app.py`: `/api/recordings/last_result` | Skips run folders whose `report.json` has `partial_run`. | Partial runs are never treated as full-run results. |
| `templates/live_log.html` | `fast` → grey "⏩ FAST" status and marker; "- Partial run (until step N)" in the heading; a **Stop run** button while the run is going. | MODE B display; Stop in both modes. |
| `templates/report.html` | "Partial run (until step N)" under the title; a "⏩ fast" pill on fast steps. | Label in the HTML report. |
| `templates/recording_editor.html` | A **▶** icon per step row; an in-app confirmation (same `modal-overlay` / `modal-dialog` style as the Add/Edit Action and Pick Element dialog) with the specified text and OK / Cancel; step 1 runs without the popup; a status line with the live-log link. | The MODE B entry point. |
| `static/js/run_control.js` (**new file**) | Polls `/api/test/run/active` every 1.5 s. While a run is active it disables every `[data-af-run-control]` control and shows a "Running: … [Stop run]" banner. | "Disable all Run icons and Replay, show Stop" on both pages. |
| `templates/index.html`, `static/js/script.js` | Loads `run_control.js`. The Replay button is marked `data-af-run-control`. `?v=` bumped so browsers load the new files. | Same rule for the dashboard. |
| `static/css/style.css` | Banner styles. | |

## 3. MODE A and MODE B

- **MODE A (full replay, the Replay button):**
  - Without `AUTOFLOW_RUN_UNTIL_STEP`, `_FAST_MODE` is never on and nothing stops early, so every step runs exactly as before.
  - New for MODE A: the Stop button (live log and banner), and its Replay buttons are disabled while any run is active.
- **MODE B (▶ on step N):**
  - Steps 1..N-1 run through the very same per-step code, with all waits, validations, Capture / Compare Value and tab steps. Only per-step screenshots are left out, and each shows "⏩ FAST".
  - Step N runs normally (screenshot, validation, full log).
  - Then the run ends: "Stopped after step N (partial run)" plus the summary.
  - A fast failure: "Could not reach step N: step X failed - reason", with that step's failure screenshot.
- **Shared by both modes:** live-log sync, Stop, the active-run lock and the existing OTP prompt all go through the one replay path.

## 4. Backup files created (`backups/phase_2/`)

- `backups/phase_2/app.py`
- `backups/phase_2/executor/run_execution.py`
- `backups/phase_2/generator/script_generator.py`
- `backups/phase_2/static/css/style.css`
- `backups/phase_2/static/js/script.js`
- `backups/phase_2/templates/index.html`
- `backups/phase_2/templates/live_log.html`
- `backups/phase_2/templates/recording_editor.html`
- `backups/phase_2/templates/report.html`
- `backups/phase_2/validation/report_generator.py` (backed up, but no change was needed)

New file (no backup): `static/js/run_control.js`.

## 5. Decisions made on my own

1. **MODE B runs the SAVED recording** (the file open in the editor), not unsaved editor changes. The server refuses the run when the editor's step N is not the saved step N. Otherwise the wrong step could run.
2. **Stop works between steps** (and during an OTP wait) through a file, because the replay is a separate process. A step already acting finishes first.
3. **A passed fast step shows "⏩ FAST"** even if it carried a warning. The warning is still in its result and the HTML report.
4. **A run stopped by the user is never reported as PASS.**
5. **Partial runs keep the normal run-folder naming** but carry `partial_run` in `report.json`. Every "last full result" lookup skips them, so they are never counted as, or shown instead of, a full result.
6. **The active-run lock is in the UI only.** The server still accepts a second run, as before, so a stale state can never block replays.
7. **"No artificial delays":** none exist in the replay (recorded pacing is never slept), so fast mode changes only screenshots.

## 6. Skipped / not possible

- Stopping **in the middle** of a long-running step (for example a chatbot reply wait) is not possible without touching the browser from another process. Stop takes effect before the next step.
- The editor has no "unsaved changes" tracking. Instead of guessing, the server-side step check refuses a mismatched step N.

## 7. Known limitations

- After clicking Stop, the run ends at the next step boundary (or ends an OTP wait). A long step finishes first.
- The disabled state follows a 1.5-second poll. For up to 1.5 s after a run starts from another page, its buttons may still look enabled. The page that started the run updates at once.
- A step added in the editor without a recorded timestamp is checked by action type only.
- Steps after N do not appear in a partial run's report at all (they were never part of it).

## 8. Manual test checklist

**MODE B (Run Until Selected Step)**

- [ ] In the editor, every step row has ▶. Click ▶ on step 1: no popup; step 1 runs normally, then "Stopped after step 1 (partial run)".
- [ ] Click ▶ on step N > 1: the in-app popup (same look as the Add/Edit Action dialog) shows "Run steps 1–N? …". Cancel does nothing; OK starts the run and opens the live log.
- [ ] The live log heading says "Partial run (until step N)". Steps 1..N-1 show grey "⏩ FAST", with no per-step screenshots in the run folder.
- [ ] Capture / Compare Value, validations and tab steps before N still run.
- [ ] Step N shows PASS / FAILED with its screenshot. Then "Stopped after step N (partial run)" and the summary "Partial run (until step N): stopped after step N…". Steps after N never run, and the browser closes as after a normal replay.
- [ ] Make a step before N fail: "Could not reach step N: step X failed - …"; that step shows FAILED with "View failure screenshot".
- [ ] Edit (but don't save) the editor so step N moves, then ▶: "Save the recording first" and nothing runs.
- [ ] After a partial run: the editor's health badges and the dashboard's "View Last Log" still show the last FULL run. The HTML report of the partial run says "Partial run (until step N)".
- [ ] An OTP step before N: the OTP prompt appears; after entering it, the run continues fast to N.

**Both modes: Stop and the lock**

- [ ] While a run (Replay or ▶) is active, every ▶ icon and every Replay button is disabled, and a "Running: … [Stop run]" banner shows on the dashboard and the editor.
- [ ] Stop run (banner, or the live log's button) ends the run before its next step: "Run stopped by the user before step K"; the remaining steps read "NOT RUN (the run was stopped by the user)"; the status is not PASS.
- [ ] Stop during an OTP prompt ends the wait and the run.
- [ ] After the run ends, the buttons are enabled again and the banner disappears.

**MODE A and existing flows**

- [ ] A normal full replay from the dashboard behaves exactly as before (no FAST steps, every step runs).
- [ ] Recording (start, stop, the rename popup).
- [ ] Pick Element and validations in the Add / Edit Action dialog.
- [ ] The existing OTP handling in a full replay.
- [ ] The live log (Running → PASS / FAILED in sync, failure screenshot link, summary).
- [ ] Timestamped screenshots and the HTML report.
- [ ] Old recordings open and replay.
- [ ] Repeat on Windows and macOS.
