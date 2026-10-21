# Phase 1 Report: Live Log Sync

Date: 14 October 2026. Only Phase 1 was implemented. Nothing was run; the only checks were static (Python parse, a compile of a generated replay script from the template, `node --check`, a Jinja parse).

## 1. Step 0 findings (how it actually works)

- **Earlier phase reports:** none (`PHASE_<n>_REPORT.md` did not exist). The earlier Edit & Rewind / Enable / Reorder work had been rolled back (`ROLLBACK_REPORT.md`), so none of it is used.
- **Storage:** a recording is a JSON file (`storage/recordings/…`, edited copies in `storage/recordings/edited/`) holding an ordered `actions` list.
  - Steps have **no ID field**.
  - Each recorded step has a unique ISO `timestamp` from the recorder. Steps added in the editor may not have one.
- **Replay:**
  - `POST /api/test/run/start` → `generate_script()` writes a standalone script with the steps embedded.
  - → `executor.start_replay()` starts it as a **separate subprocess** (its own Python process, its own Playwright **sync** API, its own browser).
  - → a watcher thread in the Flask process finishes the run.
  - The script runs `for i, step in enumerate(STEPS, start=1)`.
- **Live log channel** (already built and fairly complete):
  - The script writes `report.json` atomically at every step sub-phase:
    - `current_step` {index, phase, started_at}, published right before the action;
    - each finished step in `steps` (status, error, warning, screenshot, `started_at`, `ended_at`, `duration`);
    - extra lines in `live_log`.
  - `/api/test/run/stream` is a **Server-Sent Events** stream that re-reads that file every **0.2 s**. It sends these events:
    - `meta`;
    - `running` (step N started);
    - `step` (finished, with pass / warning / fail / skipped);
    - `step_update` (late screenshot or warning);
    - `log`;
    - `otp_needed` / `otp_resolved`;
    - `summary` (passed, warnings, failed, not run, duration, HTML report link).
  - **Handshake:** the browser action waits (at most 0.5 s) until the stream has *sent* the step's "Running" line (`.ack` file), so the log never lags behind the browser.
  - Delivery is already SSE and prompt, so no change was needed.
- **"Finished" is always produced:**
  - every normal step appends its result;
  - a step that throws gets a failed entry from the per-step `except Exception`;
  - `_StopReplay` is raised only after the result is written;
  - if the process dies, `executor._complete_steps` backfills the missing steps (failed / not run).
  - **Gap found:** the crash entry had no `started_at` / `ended_at` and `duration: 0`.
- **Failure lines:** the live log shows a plain one-sentence reason (`step_headline`, e.g. "Expected the 'Save' button…"), with technical details under a collapsed **Details**.
  - **Gap found:** the failure screenshot link was only inside Details.
- **Step list during a run:** the dashboard card (`renderReplayProgress` in `static/js/script.js`) lists every step and polls `/api/test/run/progress` every 800 ms.
  - **Gap found:** it marked the step *after the last finished one* as running (a guess). The progress endpoint never passed on the real `current_step`.
- **Run ID:** every run already has a unique `run_id` (`start_replay`).
  - **Gap found:** the events themselves did not carry it, and neither page checked it.
- **Existing OTP handling:**
  - the script writes `awaiting_otp` and waits for `run_dir/otp_input.txt`;
  - the live log shows a prompt on `otp_needed`;
  - `/api/test/run/otp_submit` writes the file.
  - Not changed in this phase.
- **Threads:** the design assumes the replay runs in a *thread* of the Flask app. **It actually runs in a separate process.**
  - Playwright objects live only in that process; Flask never touches them.
  - Communication is by files in the run folder.
  - Phase 1 needed no thread signal. Later phases (pause/resume) must use the same file-based hand-off the OTP prompt already uses: a cross-process signal instead of a `threading.Event`.

## 2. What was changed

| File : function | Change | Reason |
|---|---|---|
| `app.py`: new `LIVE_STEP_STATES`, `_DISPLAY_TO_STATE`, `_step_state()`, `_step_ref()` (next to `_step_display_status`) | The run-state vocabulary: waiting, running, passed, failed, fast, paused, stopped. Each display status maps to a state (pass/warning → passed, fail → failed, skipped/not run → stopped). The stable step reference is the recorded step's own timestamp, else `"<index>:<action type>"`. | Every event carries an extensible state and a stable step reference. Recordings are not changed. |
| `app.py`: `api_test_run_stream._sse()` | Every SSE event gets `run_id`. | So the page ignores events of other runs. |
| `app.py`: `running`, `step` (both send sites), `step_update` events | Added `step_ref` and `state`. The existing `status`, timestamps and duration are unchanged. | Index + stable reference + status + timestamps + duration on every step event. |
| `app.py`: `api_test_run_progress()` | The answer now carries `run_id`, and (while running) `current_step`. | The dashboard can mark the real running step and ignore other runs. |
| `generator/script_generator.py`: per-step `except Exception` entry in `run()` | The crashed step's result now has its real `started_at`, `ended_at` and `duration`. | Its "finished" event carries timing like every other step. |
| `templates/live_log.html` | (1) One wrapper around `source.addEventListener`: an event whose `run_id` differs from this page's run is ignored, and events without a run_id pass unchanged. (2) `markStepLine()`: each step line gets `data-state` / `data-step-ref` from Running → passed / failed / stopped, shown as a thin left marker. (3) A failed step shows **"View failure screenshot"** right under its reason (the full path stays in Details). | Run-ID filtering, row highlight in sync with the log, and a visible screenshot link. |
| `static/js/script.js`: `runRecording()` poll, `renderReplayProgress()` | A progress answer for another run is ignored. The ⏳ "Running…" row is the step the replay reports as running (`current_step`), falling back to the old guess when that is missing. | The step list highlight matches the real step. |

Nothing else was changed:
- the existing log text, layout and colours;
- the end-of-run summary line (passed, failed, … duration);
- the OTP prompt;
- the report;
- the recorder.

## 3. MODE A and MODE B

- **MODE A (full replay):** all of the above applies now: run-ID filtering, state and step reference on every event, the real running row, timing on crash results, and the failure screenshot link.
- **MODE B (Run Until Selected Step):** it does not exist yet (Phase 2). Everything above lives in the single shared path, and the `fast` / `paused` / `waiting` states are already part of the vocabulary. So MODE B will use the same events, filtering and highlighting without a second implementation. It only has to emit its new states.

## 4. Backup files created (`backups/phase_1/`)

- `backups/phase_1/app.py`
- `backups/phase_1/generator/script_generator.py`
- `backups/phase_1/static/js/script.js`
- `backups/phase_1/templates/live_log.html`

## 5. Decisions made on my own

1. **The stable step reference is the recorded timestamp**, not a new ID written into recordings. This keeps the rule "never bulk-rewrite recordings", and old recordings work unchanged.
2. **New `state` next to the existing `status`**, instead of renaming the statuses. The current UI keeps working, and later phases get the new vocabulary.
3. **Delivery left as SSE at 0.2 s, plus the existing ack handshake.** It is already prompt; switching or retuning was not needed.
4. **The "step list" highlighted is the dashboard's replay-progress list** (the list visible during a run) plus the live log's own step lines. The Recording Editor's list is not involved in a run until Phase 2 adds Run icons there.
5. **The dashboard poll interval stays 800 ms.** It is a secondary view; the live log is the SSE one.

## 6. Skipped / not possible

- **No `try/finally` was wrapped around the per-step body.** That body is thousands of lines long, and the existing `except Exception` plus post-loop and executor backfills already guarantee a finished result (Section 1). Only the missing timing on the crash result was fixed.
- **No thread signal was added.** Not needed in Phase 1, and the replay is a separate process (Section 1).

## 7. Known limitations

- `step_ref` falls back to `"<index>:<type>"` for an editor-added step without a recorded timestamp. That fallback changes if steps are inserted before it.
- Between steps (after one finishes, before the next starts) the dashboard has no `current_step`, so it shows the old "next step" guess for that moment.
- A step that is never reached because the process died shows its finished state only once the executor backfills it at the end of the run, as before.

## 8. Manual test checklist

**MODE A - new behaviour**

- [ ] Replay a recording from the dashboard: the live log shows "Step N … Running…" with a blue left marker, which turns green (PASS / WARNING) or red (FAILED) when the step finishes; the times and duration show on the line.
- [ ] While it runs, the dashboard card's ⏳ "Running…" row is exactly the step the live log shows as running.
- [ ] A failing step: a plain reason line, then "View failure screenshot" right under it, which opens the screenshot; Details still holds the technical text.
- [ ] The run's end shows the summary line (Passed / Warnings / Failed / Not run / Duration) as before.
- [ ] Start a replay, then quickly start another (or reopen a live log of an older run in the same window): the window shows only its own run's lines, never another run's.
- [ ] (Optional, developer tools) every SSE event payload has `run_id`, and step events have `step_ref` and `state`.

**MODE B**

- [ ] Not available yet (Phase 2). Nothing to test.

**Existing flows**

- [ ] Recording (start, stop, the rename popup) works as before.
- [ ] Full replay of an old recording passes as before.
- [ ] Pick Element, validate locator and the validation steps work as before.
- [ ] An OTP recording: the OTP prompt appears in the live log; entering the OTP continues the run.
- [ ] Screenshots are timestamped and named as before, and the HTML report opens.
- [ ] Old recordings open in the editor.
- [ ] Repeat on Windows and macOS.
