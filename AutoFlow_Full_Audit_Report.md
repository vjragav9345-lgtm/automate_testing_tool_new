# AutoFlow QA – Full Audit Report

## 1. Overview

Every runtime file was read line by line, and all **53,680 lines** are covered. Earlier cross-platform fixes 1–9 were re-checked in place.

**3 confirmed bugs were fixed**, each with a minimal change:

1. A live OTP could be silently lost on Mac/Linux.
2. A temp-file collision when two threads regenerate the same script.
3. The dashboard could stay stuck on "Recording" after an unexpected error.

Other findings are listed in section 4. They were either not provable from the code alone, or fixing them would change visible behaviour.

**Rules followed:**
- Nothing was run except syntax checks: `py_compile`, a compile of the rendered script template, and `node --check`.
- No new files were created other than this report and `AutoFlow_FullAudit_Progress.md`.
- No hardcoding.
- Windows behaviour is unchanged.
- Existing recordings load and replay exactly as before.

## 2. Coverage

| File | Lines | Read | Notes |
|---|---:|---:|---|
| app.py | 3897 | 100% | |
| utils.py | 21 | 100% | |
| regenerate.py | 49 | 100% | |
| requirements.txt | 5 | 100% | |
| recorder/record_session.py | 1863 | 100% | |
| recorder/action_capture.js | 7720 | 100% | |
| recorder/pick_element.py | 1518 | 100% | |
| generator/script_generator.py | 27352 | 100% | Read through a copy with comment and blank lines removed; all code and docstrings were read with their original line numbers |
| executor/run_execution.py | 696 | 100% | |
| validation/compare.py | 155 | 100% | |
| validation/report_generator.py | 481 | 100% | |
| storage/repository.py | 464 | 100% | |
| storage/retention.py | 245 | 100% | |
| storage/session_files.py | 103 | 100% | |
| static/js/script.js | 1956 | 100% | |
| static/css/style.css | 1487 | 100% | |
| templates/index.html | 327 | 100% | |
| templates/live_log.html | 724 | 100% | |
| templates/recording_editor.html | 3347 | 100% | |
| templates/report.html | 546 | 100% | |
| templates/run_stages.html | 239 | 100% | |
| templates/screenshots_viewer.html | 485 | 100% | |
| recorder/, generator/, executor/, validation/ `__init__.py` | 0 | n/a | Empty |
| **Total** | **53680** | **100%** | Counts are before the fixes. After the fixes, app.py has 3904 lines and script_generator.py has 27356 |

The chunk-by-chunk log is in `AutoFlow_FullAudit_Progress.md`.

**Excluded, as instructed. None of these are loaded by the running app:**
- `tests/`
- `generated_scripts/`, which is output that the generator rewrites
- the old project copy under `storage/`: `storage/app.py`, `storage/utils.py`, `storage/recorder/` and similar
- all `.bak*` files
- `backups/`
- `_backup_before_crossplatform/`
- `.github_push_stage/`
- logs

## 3. Fixes applied

| # | File:line | Problem | Symptom | OS | Change | Why it is safe | Backup |
|---|---|---|---|---|---|---|---|
| F1 | generator/script_generator.py:5078-5084 (inside the replay template, `_wait_for_live_otp`) | The replay deleted `otp_input.txt` even when it read it as empty. The dashboard writes that file with `write_text`, which truncates the file and then writes it. A poll landing between the two read `""` and deleted the file. | The user types the OTP and the replay ignores it, then times out with "no OTP was entered". | Mac and Linux. On POSIX the delete succeeds; Windows normally refuses to delete a file another process holds open. | The file is deleted only after a non-empty value has been read. | Success is unchanged: a non-empty value is read, deleted and used as before. Only the empty-read case differs: the file now stays, so the next poll (every `OTP_WAIT_POLL_MS`) reads the full value. The stale file from a previous run is still removed at the start of the wait. No `$` or backslash was added to the template, and the rendered template compiles. | generator/script_generator.py.bak_fullaudit |
| F2 | generator/script_generator.py:16 and :27333 (`generate_script`) | The temp file was named `<script>.py.tmp<pid>`. The recording watcher thread and the Run / Save routes run in the same process, so they share a pid. When both regenerate the same script at once, they write to the same temp file. | Rare. One call fails with `FileNotFoundError` or `PermissionError` on `os.replace`, or a replay starts on a half-written script. | All. | The temp name now also includes `threading.get_ident()`. `import threading` was added. | The final file name and atomic replace are unchanged. Each concurrent writer now has its own temp file, and the last replace wins with complete content. Cross-platform standard library only. | generator/script_generator.py.bak_fullaudit |
| F3 | app.py:889-895 (`_run_recording_session`, `finally`) | `finally` reset `active` and `recording` but not `phase`. An unexpected error left the phase stuck at "recording" or "stopping": for example after `Recorder.stop()` had already set `recording=False`, or any non-`OSError` inside `_finish_recording`. | The dashboard kept showing Recording or Stopping, and Launch stayed disabled until the server was restarted. | All. | Inside the same lock: if the phase is still launching, recording or stopping, it becomes "failed" with the same "unexpected error" message the crash path already uses. | Normal paths set "completed" or "failed" before `finally` runs, so they are untouched. The check runs in the same locked block that sets `active=False`, so a new Launch cannot interleave. | app.py.bak_fullaudit |

**Earlier fixes 1–9 were re-checked in place and are correct:**
- late-navigation watch and pointerdown handling (action_capture.js)
- `stop()` late-navigation rule, chain-close / history race, and environment captured at start (record_session.py)
- `_late_nav_not_caused` and its call sites (script_generator.py)
- `/run/report` route and the live-log link
- active-recording detection in retention
- edited environment fields
- name / run_id path containment
- `ControlOrMeta`, venv path, `action_count`
- terminal reader, macOS close detection, bounded probe
- Pick Element relaunch and idle teardown

## 4. Not fixed

### Confirmed, but fixing would change visible behaviour

- **script_generator.py ~588, `_is_duplicate_screenshot`.** It sums the 768-bin histogram as if the bins were pixel values. This is the same bug `validation/compare.py` already documents and fixes. As a result, near-duplicate screenshots are never skipped. Fixing it would make replays on every OS save fewer screenshots.

### Suspected (not provable from code alone, or needs a larger change)

1. **app.py `_cleanup_empty_dirs`.** It runs on GET of `/api/screenshots/sessions`, `/api/runs/stages` and the stage view, and it does not skip active replay folders. `_write_result` in the generated script does not create the parent folder. If the Screenshots panel is opened while a replay is still starting (its folder is empty for a few seconds), the folder is removed. This only matters if the first write is a `_write_result` outside a try block, such as a recording with explicit screenshot steps. In most cases a later screenshot recreates the folder. Fix idea: skip folders listed in `_active_replays`.
2. **repository.list_recordings.** A `recordings/*.json` file whose top level is not an object raises `TypeError` and breaks the whole dashboard list.
3. **run_execution `_watch_replay`.** It has no `try` around `_finalize_result`. An unexpected exception there leaves the run "not done" forever.
4. **run_execution `_prepare_run`.** The run_id has 1-second resolution. Two replays of the same recording started in the same second share one folder.
5. **record_session.** A navigate committed on the Timer thread exactly while `stop()` runs can be printed but missing from the saved JSON. Fixing this needs a lock around `actions`.
6. **pick_element.** The cached `resolve_and_act` module's globals are shared by concurrent picks. This is rare, since only one editor is normally open.
7. **action_capture.js ~1185.** The pick overlay set-up can run before `document.documentElement` exists, on in-picker navigations.
8. **Recording editor Pick / Validate.** They send indices computed from the in-memory list, but the server slices the saved file. These differ after an unsaved insert or delete.
9. **Recording editor ⚙ "Edit step" on a recorded step.** It replaces the whole action, which drops recorded replay hints.
10. **script.js.** After deleting the last recording, the old pagination label stays visible.
11. **script.js live log.** `window.open` runs after awaited fetches, so the browser can block the popup (Safari always).
12. **Port 5000.** It can be taken by macOS AirPlay Receiver.

### Minor or cosmetic (no functional failure)

1. **live_log.html.** After an EventSource reconnect, non-step lines can repeat and the "retrying" banner stays.
2. **report.html.** The validation icon map has no `warning` entry, so no icon is shown.
3. **style.css.** Uses Windows-only font names; Mac falls back to generic fonts.
4. **script_generator.py `_chat_fast_locate` (~10689).** The quote escape becomes a no-op in the generated script. A label containing `"` makes an invalid selector, which is caught and skipped, and the next lookup method is used.
5. **script_generator.py replay loop.** Skip branches before ~22291 (site popup not shown, hover on something not visible, double submit, merged duplicate) reuse the previous step's `count_summary_rows`, `value_range_rows` and `page_mismatch_info` in the report. No crash is possible.
6. **script_generator.py `_post_click_check`.** It returns early by design. The code after the return is intentionally unused.

### Resolved during the audit (not bugs)

- `run()` initialises `status="FAIL"`, so a replay killed before its first step is never reported as PASS.
- The template's `$$`, `\\` and raw-JS escapes were checked throughout and are correct.

## 5. Known limits

- **SyntaxWarnings.** The replay template is a non-raw string containing sequences like `\d` and `\s`. Python 3.12 shows a SyntaxWarning (for example at line 1601) when the generator is compiled or imported. This is harmless today but would become an error in a future Python version. It is pre-existing and was not changed, because editing the template would touch many lines.
- **Static review only.** The audit could not prove timing-dependent behaviour such as Chromium init-script timing or the macOS window and process lifecycle. Those items are listed as suspected.
- **Untested fixes.** F1–F3 were verified only by reading the code, compiling it, and compiling the rendered template. They were not run.

## 6. Test checklist (run on Mac and on Windows)

**Core flows**
1. Start the app, then:
   - Launch a recording, click and type on a site, use Pick Element, drag a slider.
   - Stop with Stop Recording. Then repeat and stop by closing the browser window. On Mac, close the last window and confirm the session ends.
2. Open the recording in the editor and:
   - edit a value and save;
   - rename it;
   - delete a step and save;
   - replay it.
3. During the replay, check:
   - the live log updates;
   - the HTML report opens;
   - the Screenshots viewer and run stages show images;
   - Cleanup preview works.

**F1 (OTP)**

4. Replay a recording with an OTP step.
5. When "Enter OTP to continue" appears, submit the code from the dashboard.
6. Confirm the replay continues with that code. Repeat 3–5 times; it should never time out after a submit.

**F2 (script regeneration)**

7. Save a recording in the editor and immediately click Run.
8. Also edit a recording JSON on disk, which triggers the watcher, and click Run straight away.
9. The replay must start normally. No `.tmp<pid>_<thread>` file should be left in `generated_scripts/` after a normal run.

**F3 (stuck phase)**

10. Normal stop: the dashboard shows Completed, and Launch is enabled again.
11. Failed launch with an unreachable URL: it shows Failed, and Launch is enabled again.
12. If a session ever ends with an error, the dashboard must show "RECORDING STOPPED - an unexpected error interrupted the session", and Launch must be enabled without restarting the server.

**Regression**

13. Replay a few existing recordings made before these changes. Results should match previous runs.

## 7. Rollback

Each changed file has a backup made just before its first edit:

| Restore | From |
|---|---|
| `app.py` | `app.py.bak_fullaudit` |
| `generator/script_generator.py` | `generator/script_generator.py.bak_fullaudit` |

On macOS or Linux:
```
cp app.py.bak_fullaudit app.py
cp generator/script_generator.py.bak_fullaudit generator/script_generator.py
```

On Windows:
```
copy /Y app.py.bak_fullaudit app.py
copy /Y generator\script_generator.py.bak_fullaudit generator\script_generator.py
```

After restoring, restart the app. Scripts are regenerated on the next save or run.

`_backup_before_crossplatform/` and all older `.bak` files were left untouched.
