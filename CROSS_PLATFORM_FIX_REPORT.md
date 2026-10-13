# AutoFlow QA – Cross-Platform Fix Report

Scope: make the existing Windows behaviour work the same on Windows, macOS and Linux, without changing what the tool does.
Method: read the code, plus the Playwright 1.47 driver source bundled in `venv/`, plus the recordings this Mac produced on 2026-10-08. Nothing was run: no app, no recordings, no replays, no tests. Nothing in this report has been tested.

---

## 1. Phase 0 – Architecture map

**Live code:** `app.py`, `utils.py`, `recorder/record_session.py`, `recorder/action_capture.js`, `recorder/pick_element.py`, `generator/script_generator.py`, `executor/run_execution.py`, `validation/*`, `storage/repository.py`, `storage/retention.py`, `storage/session_files.py`, `static/js/script.js`, `templates/*.html`.
`storage/` also holds an old copy of the project (`storage/app.py`, `storage/utils.py`, `storage/recorder/…`). None of it is imported, so it was left untouched.

**Record → capture → close → save → popup**
1. The dashboard "Launch Browser" button calls `POST /api/browser/launch` (`app.py: api_browser_launch`). This sets `session_state.active=True` and `phase="launching"`. It then starts **one daemon thread per session** running `_run_recording_session`, and waits on `ready_event`.
2. That thread owns the whole Playwright lifecycle, because the sync API is tied to its thread:
   - `sync_playwright().start()`, `chromium.launch(headless=False)`, `new_context()`, `new_page()`
   - `Recorder.install_context_capture(context)`, which registers a context-level `expose_binding("recordAction")` and `add_init_script(action_capture.js)`. The capture script is therefore re-injected on every document load: navigation, reload, and new tabs.
   - Then `goto`, a screenshot, `recorder.start()`, and `phase="recording"`.
3. Capture:
   - Page JS calls `recordAction(json)`, which reaches `Recorder._on_action_binding` and then `_on_action`, which calls `_record`. `_record` appends a line to `.draft.jsonl` and periodically rewrites the draft `.json`.
   - Navigations are recorded from Python via `page.on("framenavigated")` (`_on_navigate`), committed on a `threading.Timer`.
   - Tab opens and closes are recorded via `context.on("page")` and `page.on("close")`.
4. Liveness/stop loop (in `_run_recording_session`), every 0.5 s:
   - `browser.is_connected()`
   - `recorder.get_any_open_page()`
   - a probe call on that page (this is also the only point where Playwright events and bindings are pumped)
   - `enter_pressed.wait(0.5)`

   It stops when either of these happens:
   - Terminal ENTER or the dashboard's Stop Recording button (`/api/recording/stop`) sets `enter_pressed`.
   - The browser or pages are detected as closed (`browser_closed`), or the probe fails 10 times in a row (`navigation_error`).
5. Save: `_finish_recording` calls `Recorder.stop()`, then `repository.save_recording()` (atomic temp file + `os.replace`). It then regenerates the script and sets `phase="completed"` along with `last_recording_path` and `last_recording_name`. The `finally` block runs `browser.close()` and `pw.stop()`.
6. Popup: this is a **web** modal, not a native GUI dialog. There is no tkinter anywhere. `static/js/script.js: renderRecordingStatus` polls `/api/recording/status` every 1 s while the phase is launching, recording or stopping. When the phase changes from active to `completed`, it calls `openNameTestModal()` and `loadRecordings()`.
7. Replay: `/api/test/run/start` regenerates the script (`generate_script`) and then calls `executor.start_replay`. That starts `subprocess.Popen` of the generated script, plus a `_watch_replay` thread that runs `_finalize_result` and marks the run done. The dashboard polls `/api/test/run/progress`; the live-log popup reads `/api/test/run/stream` (SSE).
8. Pick Element: `recorder/pick_element.py` runs one "warm session" thread per editor tab. Each owns its own Playwright, browser and context, and runs a wait loop until the user picks an element, closes the window, or 120 s pass.
9. Flask: `app.run(host="127.0.0.1", port=5000, debug=False, threaded=True)` inside `if __name__ == "__main__":`. There is no reloader and no multiprocessing. A watchdog observer watches `storage/recordings/`.

**OS-sensitive spots found**

| # | Location | What |
|---|---|---|
| A | `app.py: _run_recording_session` loop | Treats `browser.is_connected()` (the browser *process* exiting) as the authoritative "browser closed" signal. It is pumped by an `evaluate("1")` call that has no timeout. |
| B | `app.py: _run_recording_session` `_wait_for_enter` | A new `input()` thread is started per session and never ends when the session ends another way. |
| C | `recorder/pick_element.py` wait loop and `_WarmPickSession._browser_alive` | "Picker window closed" is detected only through `browser.is_connected()`. |
| D | `recorder/pick_element.py: _advance_to` | Relaunches without stopping the previous Playwright/browser. |
| E | `generator/script_generator.py:3895` | `el.press("Control+A")` used as select-all. |
| F | `executor/run_execution.py: _build_command` | Hardcoded Windows venv layout `venv/Scripts/python.exe`. |
| G | `executor/run_execution.py: _watch_replay` | `NameError` on `action_count`. This affects every OS, not only macOS. |
| H | `recorder/record_session.py: _capture_dom_snapshot` | Stores a path with OS-native separators in the recording JSON. |
| I | `app.py` `port=5000` | Port 5000 is used by macOS AirPlay Receiver. Not changed; see §3. |

**Evidence from this Mac (2026-10-08).** Times are IST; the recording timestamps are UTC, i.e. IST − 5:30.
- `session_20261008_172051`: last action 17:20:57. It wrote a DOM snapshot for its last navigation at 17:21:00, and was saved at 17:21:02 with `stop_reason=browser_closed`. Close was detected about 1–2 s after the window closed.
- `session_20261008_172151`: last action 17:21:54, which was a click on a *new* results page, so a navigation had happened. It was **saved only at 17:25:21**, still with `stop_reason=browser_closed`. Unlike session 1, no DOM snapshot and no `expected_url` were recorded for its last navigation.
- The loop exits with `browser_closed` only from its close checks. So for about 3.5 minutes the session did not register that the window had closed, and it only finished at the moment the browser became disconnected (for example, quitting Chromium).
- There is no third screenshots folder, so a third launch, if one was tried, never reached its first screenshot.

---

## 2. Issues and fixes

### Phase 1 – Browser close detection, save, popup

#### 1.1 Recording end depended on the browser process exiting
- **Symptom (Mac):** after closing the browser, the recording is not saved (or is saved minutes later), and the "Name this test" popup does not appear.
- **Root cause.** In `app.py: _run_recording_session`, the liveness loop:
  - The first check is `if not browser.is_connected()`. On Windows, closing the last window ends the Chromium process, so this check fires immediately and every pending Playwright call fails at once.
  - On macOS, Chromium keeps running with no window. Playwright launches it with `--no-startup-window` and has nothing macOS-specific to make it quit (`driver/package/lib/server/chromium/chromium.js: defaultArgs`). So `is_connected()` stays `True`.
  - That leaves only the page-close event, which is processed only while the loop is inside its probe `probe_page.evaluate("1")`.
  - `evaluate` has **no timeout**. If that one call doesn't come back, the loop is stuck: no close check, no Stop/ENTER check, nothing saved. On Windows, the process exit would release it. On macOS nothing does until the browser process is quit, which matches session 2's 17:25:21 save exactly.
- **The popup is a consequence, not a separate bug.** The frontend only opens the modal when the phase moves to `completed`, and `_finish_recording` was never reached. `api_browser_launch` resets the per-session flags, and the frontend's poll timer is reset on every transition. The only state carried between sessions is the leftover stdin thread, covered in 2.1.
- **Fix (`app.py: _run_recording_session`):**
  1. The close check is now `if not browser.is_connected() or not context.pages:`, and the same extra condition is added in the probe's failure branch. `context.pages` is Playwright's own list of open pages in the recording context. "No page left" means "the user closed the browser" on every OS, whether or not the process exits.
  2. The probe is now `probe_page.wait_for_function("1").dispose()` instead of `probe_page.evaluate("1")`.
     - In the driver (`server/frames.js: _waitForFunctionExpression`), the expression is evaluated **immediately**, with no animation-frame wait. So on a responsive page it returns as fast as `evaluate`, and on a closed page it fails just as fast.
     - It is bounded by the page's existing default timeout (`page.set_default_timeout(8000)`, already set for the recording page and for every new tab), and the driver enforces that bound even if the renderer never answers.
     - A timeout counts as one probe failure, exactly like an `evaluate` error always did. So the existing `navigation_error` rule (10 consecutive failures) is unchanged.
     - `.dispose()` releases the handle so nothing accumulates over a long recording.
- **Why it is permanent and generic:** it uses only Playwright's own page/context state and an existing timeout. There are no sleeps, retries, site checks, or new constants.
- **Why Windows is unaffected:**
  - On Windows, closing the window makes `is_connected()` False, which is the first operand, so it still fires first, as before.
  - `context.pages` can only be empty when no window is left, which on Windows coincides with the process exit.
  - On a healthy page, `wait_for_function("1")` returns immediately with the same result as `evaluate("1")`, and on a closed page it raises the same way. The only behaviour that changes is the case where `evaluate` would have waited forever.
- **What is not certain:** the exact Chromium/macOS condition that kept session 2's probe from returning cannot be shown from code alone. The fix removes the dependence on that one unbounded call and on the process exit, which are the two mechanisms the evidence points to. Checklist item M3 is there to confirm it.

#### 1.2 Save timing
- `_finish_recording` → `Recorder.stop()` → `repository.save_recording()` already runs on every stop path: ENTER, Stop button, browser closed, navigation error, and the crash handler. Actions are also written one by one to the `.draft.jsonl` sidecar, and drafts are recovered on start-up and at each new session.
- With 1.1 in place, the save no longer waits for a Windows-only signal. No other change was needed.

### Phase 2 – "Stuck on third run" / resource cleanup

#### 2.1 Leaked terminal-ENTER threads steal ENTER from later sessions
- **Symptom:** after a session ends by closing the browser or by Stop Recording, pressing ENTER does not stop a later recording, so that recording appears stuck. Each session also leaves one more thread blocked on stdin.
- **Root cause (`app.py: _run_recording_session`):**
  - Each session started its own `_wait_for_enter` thread calling `input()`. That thread only ended when ENTER was pressed.
  - The next ENTER is read by the **oldest** blocked thread, which sets the `Event` of a session that has already finished.
  - Several threads calling `input()` on the same terminal at once is also something CPython only recently stopped crashing on (GH-123321).
  - This bug exists on every OS. It matches "a later run hangs" whenever ENTER is used to stop.
- **Fix:** one process-wide `_terminal_enter_reader` thread, started by the first recording session. It reads lines for the life of the process and sets **whichever session's `Event` is current** (`_recording_control["enter_pressed"]`, read under `state_lock`).
  - The EOF handling (no terminal attached) is kept as it was: log the warning, show the same dashboard message, and never auto-stop.
  - Later sessions in that situation get the same message straight away (`_NO_TERMINAL_MESSAGE`, same text as before).
- **Why Windows is unaffected:** the first session behaves exactly as before. Later sessions now get the stop that was always intended. ENTER pressed while no session is active is ignored, as it effectively was before, when a stale thread consumed it.

#### 2.2 Pick Element: closed picker window not detected on macOS, and browsers/drivers leaked
- **Symptom (Mac):** after closing the Pick Element window, the picker waits out the full 120 s and then reports "timeout" (Windows reports "cancelled" immediately). The warm session treats a windowless Chromium as alive, and a relaunch overwrites the previous Playwright instance without stopping it.
- **Root cause (`recorder/pick_element.py`):**
  - `_run_pick_wait_phase` loops `while … browser.is_connected()` and reports "cancelled" only on `not browser.is_connected()`.
  - `_WarmPickSession._browser_alive()` is just `is_connected()`. This is the same macOS process-lifetime difference as 1.1.
  - `_advance_to` calls `_launch()` (`self.pw = sync_playwright().start()`) when the browser is "not alive", without stopping the previous `self.pw`.
  - The idle path only tore down browsers that were still "alive", so a windowless or disconnected one was never released.
- **Fix:**
  - New helper `_picker_window_open(browser)`: `browser.is_connected() and any(ctx.pages for ctx in browser.contexts)`. It is used in the wait-loop condition, the "cancelled" branch, and `_browser_alive()`.
  - `_advance_to` now calls `_teardown_browser()` before `_launch()`.
  - The idle branch also tears down whenever a Playwright instance is still held (`elif self.pw is not None`).
- **Why Windows is unaffected:**
  - On Windows, a context with no pages only happens when the process has exited, so the helper gives the same answer as `is_connected()`.
  - `_teardown_browser()` on an already-dead browser only calls `pw.stop()`, releasing the driver process that was previously leaked.

#### 2.3 Checked and found fine
- **No persistent profile** (`launch_persistent_context` / `user_data_dir`) is used anywhere. Every launch gets a fresh temp profile, so there are no profile locks.
- **Every Playwright instance is created and stopped on its own thread.** Recording, one-shot pick, warm pick, `validate_locator` and `test_navigate` each use `try/finally` with `browser.close()` and `pw.stop()`. Replays run in a separate process.
- **No `multiprocessing`.** `app.py` and `regenerate.py` both have `if __name__ == "__main__":` guards.

### Phase 3 – Dashboard refresh / keyboard shortcuts

#### 3.1 Select-all via `Control+A` in replay
- **Symptom (Mac):** replaying a Fill into a rich-text (contenteditable) field that `Locator.clear()` can't clear adds the text to the existing content instead of replacing it.
- **Root cause:** `generator/script_generator.py:3895`, in the fill helper's contenteditable fallback, calls `el.press("Control+A")` and then `Backspace`. Playwright's macOS key map (`driver/package/lib/server/macEditingCommands.js`) maps `Control+KeyA` to `moveToBeginningOfParagraph:`; select-all on macOS is `Meta+KeyA` → `selectAll:`.
- **Fix:** `el.press("ControlOrMeta+A")`. Playwright resolves this to `Meta` only on darwin and to `Control` everywhere else (`server/input.js: resolveSmartModifierString`).
- **Why Windows is unaffected:** on Windows and Linux it resolves to the identical `Control+A`. Every replay regenerates its script (`/api/test/run/start` calls `generate_script`), so existing recordings pick this up with no action needed.

#### 3.2 Refresh (reload) during recording and replay – reviewed, nothing OS-specific found
- **Recording:**
  - The recorder records only Enter, Tab, Escape and Backspace as key steps (`action_capture.js` `MEANINGFUL_KEYS`). No modifier shortcut is ever recorded or replayed, so no recording contains `Control+R`.
  - Every `preventDefault`/`stopImmediatePropagation` in the injected script is gated by `window.__afqaPickMode` (Pick Element only). So nothing blocks Cmd+R / F5 / the reload button while recording.
  - The capture script is installed with a **context-level** `add_init_script`, so Playwright re-runs it on every document load, reload included, on every OS.
- **Navigation recording:** a reload lands on the same URL, and `_on_navigate` deliberately ignores same-URL navigations ("no navigation"). That is existing, intended behaviour on Windows too, so it was not changed.
- **Shared cause with 1.1:** if the page's refresh appeared not to work *while recording on Mac*, the stalled recording loop in 1.1 is the most likely shared cause, since events and bindings stop being processed. Checklist item M5 covers this.

### Phase 4 – Whole-project sweep

#### 4.1 Async replay never finished (`NameError`) – all OSes
- **Symptom:** after a dashboard replay, the run never reports "done": the button stays busy and the live log never shows a summary. Each run also leaves its SSE stream generator polling forever on the server.
- **Root cause:** `executor/run_execution.py: _watch_replay` calls `_finalize_result(…, action_count=action_count)`, but `action_count` is not a parameter or variable there. Every async replay raises `NameError` in the watcher thread after the subprocess exits, so `_active_replays[run_id]["done"]` is never set. The same line is in the `.bak_v4_diag` copy, and older backups don't have it.
- **Fix:** `_watch_replay` gains `action_count=None`, and `start_replay` passes it through `kwargs`. This is the value `execute_test` already passes.
- **Why Windows is unaffected:** this restores the intended completion path on every OS. Nothing else changes.

#### 4.2 Hardcoded Windows venv interpreter
- **Root cause:** `executor/run_execution.py: _build_command` always looked for `venv/Scripts/python.exe`, which never exists on macOS or Linux. So replays there silently used whatever interpreter was running the server.
- **Fix:** under `sys.platform == "win32"` it keeps `venv/Scripts/python.exe`; otherwise it uses `venv/bin/python`. The existing `sys.executable` fallback is kept.
- **Why Windows is unaffected:** the Windows branch is the original line, unchanged.

#### 4.3 Recording JSON stored an OS-native path
- **Root cause:** `recorder/record_session.py: _capture_dom_snapshot` returned `str(relative_path)`, which gives `storage\snapshots\…` on Windows. A POSIX system reads that as one filename. Every other path the app stores is "/"-separated (`.replace("\\", "/")` throughout `app.py` and `run_execution.py`).
- **Fix:** `.as_posix()`.
- **Why Windows is unaffected:** the field is forensic only. Replay never reads it, and its one consumer (`tests/fixture_from_snapshot.py`, `BASE_DIR / path`) accepts "/" on Windows.

#### 4.4 Checked and found fine
- **Filenames:** run folders, screenshots, scripts and snapshots are built with `_slug()` (alphanumerics and `_`) and timestamps using `-`/`_`. None contain `: * ? < > | " /`.
- **Encoding:** every text read and write in the live Python files passes `encoding="utf-8"`.
- **Write locations:** everything is written under the project folder (`storage/`, `generated_scripts/`, `screenshots/`), which is writable.
- **Case:** filename references match on-disk case.
- **Platform calls:** no `os.startfile`, `explorer`, `start`, `cls`, `winreg`, `msvcrt` or `CREATE_NO_WINDOW` in project code, and no `shell=True` or Windows shell syntax in subprocess calls.
- **Browser launch:** no `--start-maximized`.
  - Recording uses the default 1280×720 viewport.
  - Replay uses `--window-position=0,0 --window-size=1280,900`, which Chromium honours on all three OSes.
- **Flask:** `debug=False`, so there is no reloader double-start. It binds to `127.0.0.1`.
- **Frontend:**
  - There are no `ctrlKey`-only shortcuts; the tool's UI only uses Enter and Escape.
  - The frontend handles no file-system paths itself; the server normalises paths to "/".
- **requirements.txt:** Flask, playwright, Pillow, Jinja2 and watchdog all install on macOS and Linux. watchdog uses FSEvents on macOS, and the handler covers created, modified and moved events, which is what an atomic `os.replace` produces there.

---

## 3. Deliberately not changed

| Item | Why |
|---|---|
| Port 5000 (`app.py`) | macOS 12+ AirPlay Receiver also listens on port 5000. Changing the port would change behaviour on Windows. The app already runs on this Mac, so the port is usable here. If it ever fails with "Address already in use", turn off System Settings → General → AirDrop & Handoff → AirPlay Receiver. |
| Reload not recorded as a step | Existing, intended behaviour on Windows (same-URL navigation is ignored in `_on_navigate`). Changing it would change recordings. |
| Replay crash-recovery relaunch (`script_generator.py` ~26590) | When every page has closed, macOS can leave the old windowless Chromium alive alongside the relaunched one. It is cleaned up when the replay process exits, because Playwright's driver closes its browsers when it stops. That is bounded, and touching it would change the replay engine. |
| `browser.close()` / `pw.stop()` have no timeout | Adding one would be a workaround. With 1.1 the loop no longer gets stuck before reaching teardown. |
| Live-log popup in Safari | `window.open` runs after `await fetch(...)`, which Safari's popup blocker blocks. Replay still runs, and progress still shows on the dashboard. This is browser behaviour, not OS behaviour, and the code already treats a blocked popup as a no-op. Using Chrome/Edge for the dashboard on Mac matches Windows. |
| `SyntaxWarning: invalid escape sequence '\d'` (`script_generator.py:1600`) | Pre-existing and not OS-related. The backup triggers it too. |
| Old project copy under `storage/` and the `*.bak*` files | Not imported, so they have no effect. |
| Mac Chromium's missing UA/locale in the saved recording when stopped by closing | `Recorder.stop()` reads these from the already-closed page, so they come out `None`. This is the same on Windows (see existing recordings) and is not OS-specific. |

---

## 4. Modified files and backups

| Modified file | Backup |
|---|---|
| `app.py` | `_backup_before_crossplatform/app.py` |
| `recorder/pick_element.py` | `_backup_before_crossplatform/recorder/pick_element.py` |
| `recorder/record_session.py` | `_backup_before_crossplatform/recorder/record_session.py` |
| `executor/run_execution.py` | `_backup_before_crossplatform/executor/run_execution.py` |
| `generator/script_generator.py` | `_backup_before_crossplatform/generator/script_generator.py` |

New file: `CROSS_PLATFORM_FIX_REPORT.md`.
All edited files were syntax-checked with `ast.parse`, which only parses the code and does not run it.

---

## 5. Manual test checklist

Run every item on **Windows** first (reference behaviour), then on **macOS**. Start the server from a terminal with `python app.py`, and keep the terminal visible.

**Recording and close**
- [ ] **M1 – record and close by window:** Launch a URL, do 3–5 actions including a link click that navigates, then close the window (Windows: X; Mac: red button or Cmd+W).
  - Within about 1–2 s the terminal prints `RECORDING COMPLETED … Stop reason: browser_closed`.
  - The dashboard shows "Recording Completed" and the "Name this test" popup.
- [ ] **M2 – saved steps:** Open the new recording.
  - Every action you did is present, including the navigation result on the clicked link (`expected_url`).
  - `storage/recordings/` has no leftover `.draft.jsonl` for it.
- [ ] **M3 – close right after a navigation:** Click a link and close the window while the next page is still loading. Saving must still happen within a few seconds (this is the session-2 case).
- [ ] **M4 – Mac only, Chromium left running:** after M1, check that no "Chromium"/"Google Chrome for Testing" icon stays in the Dock a few seconds after saving.
- [ ] **M5 – refresh while recording:** On your dashboard site, press the site's own refresh button, then Cmd+R (Mac) / F5 or Ctrl+R (Windows), then do 2 more clicks.
  - The page reloads.
  - The clicks after the reload are recorded.
- [ ] **M6 – stop methods:** Run 3 sessions back to back, stopping them with:
  1. Stop Recording
  2. closing the window
  3. ENTER in the terminal

  Session 3 must stop on ENTER.
- [ ] **M7 – 3+ consecutive runs:** Launch → record → close → name, at least 4 times in a row without restarting the server. Every run saves, shows the popup, and the next Launch starts normally.

**Pick Element (Recording Editor → Add Action → Pick Element)**
- [ ] **P1:** Pick an element normally. The selection is returned.
- [ ] **P2:** Open the picker and close its window without picking. The modal reports cancelled straight away on both OSes, not after 2 minutes.
- [ ] **P3:** Do P2 and then P1 again twice. Each picker opens a fresh window, and on Mac no extra Chromium stays in the Dock afterwards.

**Replay**
- [ ] **R1:** Replay a recording from the dashboard.
  - It finishes.
  - The result panel shows PASS/FAIL with a report link.
  - The live-log window shows a final summary.
- [ ] **R2:** Replay 3 times in a row. Each one completes and the button becomes usable again.
- [ ] **R3:** Replay a recording that fills a rich-text editor (contenteditable) that already has text. The field ends up containing only the recorded value.
- [ ] **R4:** Replay a recording that includes a page refresh step or a navigation back to the dashboard. The page loads and the next step runs.
- [ ] **R5 – Mac only:** confirm the replay started with `venv/bin/python`, either in the terminal or with `ps aux | grep _script.py` during a run.

**General**
- [ ] **G1:** A recording made on Windows, copied to the Mac, opens in the editor and replays (and the reverse).
- [ ] **G2:** Start the server in an environment without a terminal (for example the VS Code Run button). Recording shows the "no terminal input available" message and stops with Stop Recording.
