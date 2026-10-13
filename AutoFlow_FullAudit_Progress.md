# AutoFlow QA – Full Audit Progress

Resume rule: continue from the last recorded range of the first file that is not yet "DONE". Never restart, never skip.

## Runtime files (total lines)

| File | Lines | Status |
|---|---|---|
| app.py | 3897 | |
| utils.py | 21 | |
| regenerate.py | 49 | |
| requirements.txt | 5 | |
| recorder/__init__.py | 0 | empty |
| recorder/record_session.py | 1863 | |
| recorder/action_capture.js | 7720 | |
| recorder/pick_element.py | 1518 | |
| generator/__init__.py | 0 | empty |
| generator/script_generator.py | 27352 | |
| executor/__init__.py | 0 | empty |
| executor/run_execution.py | 696 | |
| validation/__init__.py | 0 | empty |
| validation/compare.py | 155 | |
| validation/report_generator.py | 481 | |
| storage/repository.py | 464 | |
| storage/retention.py | 245 | |
| storage/session_files.py | 103 | |
| static/js/script.js | 1956 | |
| static/css/style.css | 1487 | |
| templates/index.html | 327 | |
| templates/live_log.html | 724 | |
| templates/recording_editor.html | 3347 | |
| templates/report.html | 546 | |
| templates/run_stages.html | 239 | |
| templates/screenshots_viewer.html | 485 | |
| **Total** | **53680** | |

Excluded (not loaded by the app, per instructions): tests/, generated_scripts/, old project copy under storage/ (storage/app.py, storage/utils.py, storage/recorder/, …), *.bak*, backups/, .github_push_stage/, logs.

## Chunk log

- utils.py 1–21 (DONE). No issues.
- regenerate.py 1–49 (DONE). Note: regenerates from raw JSON without repository.migrate_recording (generate_script itself calls migrate – to verify in script_generator). No issue yet.
- requirements.txt 1–5 (DONE). All cross-platform. No issues.
- storage/session_files.py 1–103 (DONE). No issues.
- storage/repository.py 1–464 (DONE). Notes: list_recordings only catches JSONDecodeError/OSError – a recordings/*.json whose top level is not an object (or actions not a list) raises TypeError/AttributeError and breaks the whole dashboard list (SUSPECTED – needs a malformed file; low). Otherwise OK.
- storage/retention.py 1–245 (DONE). Re-check of earlier fix #7: correct. Correction to its earlier description: cleanup is age-based (≥30 days), so a live draft (fresh mtime) was never at risk; the real effect of the old bug was that old recordings were not protected while a recording session ran. No new issues.
- validation/compare.py 1–155 (DONE, read in full earlier this session via cat). No issues (paths via pathlib, PIL cross-platform).
- validation/report_generator.py 1–481 (DONE). Note: when generate_report gets no output_dir the report lands in reports/, which /run/report (earlier fix #6) does not serve (only generated_scripts/screenshoots/). All live callers pass the run folder (run_dir always set, even in _fail_result), so no user-visible effect – noted only.
- executor/run_execution.py 1–696 (DONE; 517–533/617–619/668–685 are comment-only lines, also read in the previous session). Earlier fixes (venv path, action_count) confirmed correct.
  - SUSPECTED: _watch_replay has no guard around _finalize_result – any unexpected exception there leaves the run "not done" forever (dashboard spinner + SSE loop). Fix idea: try/except that stores a _fail_result.
  - SUSPECTED: _prepare_run run_id has 1-second resolution – two replays of the same recording started in the same second share a folder.
  - TO VERIFY in generator: initial raw "status" before the first step – if it is not "FAIL", a run killed before writing any step could be reported as PASS (since _complete_steps only runs when steps is non-empty).
- app.py 1–906 (read: 1–23, 24–65, 66–160, 160–370, 370–560, 560–906; comment-only lines filtered in 160–906 were read in the previous session). Earlier fixes (terminal reader, close detection, bounded probe) re-checked: correct.
  - CONFIRMED (state machine): _run_recording_session finally resets active/recording but not "phase"; any unexpected exception after Recorder.stop() set recording=False (or before ready_event in a branch that doesn't set phase) leaves phase "recording"/"stopping" forever → dashboard shows Recording and Launch stays disabled until server restart (script.js disables Launch while phase is active). Fix: in finally, if phase is still launching/recording/stopping → "failed" with a message.
  - Note (to verify generate_script write): watcher regeneration and _finish_recording/api_test_run_start regeneration can write the same script concurrently.
- app.py 905–1434 read earlier this session (Read tool, full). No new issues beyond the earlier list.
- app.py 906–3897 (read: 905–1434 earlier this session; 1435–1700; 1697–1990; 1990–2300; 2300–2560; 2560–2760; ~2757–3056 earlier this session; 3020–3260; 3256–3500; 3500–3560; 3495–3816 earlier this session; 3810–3897). app.py DONE (1–3897, no gaps). Method note: in some chunks comment-only/blank lines were filtered from the printout; all code lines were read.
  - Re-check fixes #6 (/run/report), #8 (edited env fields), #9 (name/run_id containment): correct.
  - Note: /api/screenshots/* and /api/runs/stages call _cleanup_empty_dirs on GET; a replay's brand-new empty run folder could be removed before its first write (TO VERIFY: generator _write_result creates parent dir?).
  - Note: progress route and SSE stream can both generate report.html / rewrite report.json at once (same content, failures swallowed) – harmless.
- recorder/record_session.py 1–1863 (DONE): every line read across the previous two sessions (1–130, 130–339, 339–678, 675–800, 800–960, 949–1349, 1350–1807 of the pre-edit file) plus today's edited regions re-read in the diff review; 1–65 re-read now. Re-check fixes #2 (stop() late-nav rule), #3 (chain close / history race), #5 (env at start): correct, no conflicts.
  - SUSPECTED (both OS, narrow race): a navigate commit running on its Timer thread at the exact moment stop() runs can append after stop() sorted self.actions → that one navigate is printed but missing from the saved JSON. Fix would need a lock around self.actions – not minimal; left.
- recorder/pick_element.py 1–1518 (DONE): 1–240, 262–560, 549–830, 1505–1518 now; 240–262 earlier today; 820–1502 in the previous session (edited lines re-read in diff). Re-check of previous-session fix (_picker_window_open, teardown before relaunch, idle teardown): correct.
  - SUSPECTED (both OS): the cached resolve_and_act module is shared by every pick/validate thread, so its module-level globals (step warnings, notes) are shared between concurrent picks. Rare (one editor normally); not fixed.
- static/js/script.js 1–1956 (DONE: 1–180, 180–660 earlier today, 652–1000, 1000–1330, 1330–1630, 1630–1770 earlier today, 1757–1956). All fetch URLs/methods/bodies match app.py routes. No confirmed bug.
  - SUSPECTED (cosmetic): deleting the last recording leaves the old pagination label visible (loadRecordings returns early without hiding pagination).
  - SUSPECTED (carried from Phase 1): live-log window.open runs after two awaited fetches – popup can be blocked (Safari always; others when start is slow).
- templates/index.html 1–327 (DONE). Every id script.js reads exists (connectDbBtn/systemStatusBtn are absent but script.js null-checks them). No issues.
- templates/live_log.html 1–724 (DONE). Fix #6 link verified. Cosmetic only (not bugs per rules): after an EventSource auto-reconnect the server restarts the stream, so non-step "log" lines can repeat and the "retrying..." banner is never cleared. No change.
- templates/run_stages.html 1–239 (DONE). No issues.
- templates/screenshots_viewer.html 1–485 (DONE; 1–111 markup ids checked). No issues.
- templates/report.html 1–546 (DONE). Cosmetic only: validation-card icon map (line 121) has no 'warning' key → a warning validation step shows no icon (Jinja renders empty, no crash). No change.
- static/css/style.css 1–1487 (DONE, condensed printout of every rule). No functional issues (Windows-only font names fall back to generic fonts on Mac – cosmetic).
- recorder/action_capture.js 1–1300 (read). Pick-mode overlay/drag-select code.
  - SUSPECTED (both OS, Pick Element only): line 1185 calls _afqaSetupPickOverlay() immediately; it appends to (document.body || document.documentElement) and observes document.documentElement. When this runs as an init script on a NEW document inside the picker (page redirect/Back), documentElement does not exist yet (this file's own scroll-section comment says so), so it would throw and abort the rest of the script for that page (no overlay, clicks reach the site). Fix idea: defer setup to DOMContentLoaded when documentElement is null. Not fixed (behaviour of Chromium at init time not provable from code alone).
- recorder/action_capture.js 1300–4560 (read). No confirmed bugs (XPath literal escaping with backslash in buildXpathCandidates only yields an invalid candidate that is discarded).
- recorder/action_capture.js 4560–7720 (read; 4560–4745 and 7370–7470 earlier today). action_capture.js DONE (1–7720). Re-check fix #1 (late-navigation watch: pointerdown + userInitiated): consistent with this file's own pointerdown fallback (afqaPd, ~line 5990) which already exists because sites cancel mouse events; no conflict. No other confirmed bugs (Mac trackpad momentum scrolling is debounced by SCROLL_SETTLE_MS; Ctrl+click on Mac arrives as contextmenu → recorded as right_click, same as a Windows right-click).
- templates/recording_editor.html 1–3347 (DONE: 1–420, 420–840, 840–1270, 1270–1700, 1700–2130, 2130–2560, 2560–2990, 2986–3347). All fetch routes/bodies match app.py.
  - SUSPECTED / design (both OS): Pick Element, Prewarm and Validate send insert_after_index computed from the IN-MEMORY (possibly unsaved) action list, but app.py slices the SAVED file – after an unsaved delete/insert the replayed prefix can differ from what the editor shows. Fix needs sending the in-memory actions (API change) – not minimal; not fixed.
  - SUSPECTED / design (both OS): "Edit step" (⚙) on a RECORDED step replaces the whole action with a new minimal one (new timestamp, xpath-only locator_profile, no post_click/expected_url/hover_chain/bounding_box). Probably intended as "re-define this step", but it silently drops recorded replay hints. Not changed (behaviour change).
- generator/script_generator.py 1–1300 (read). CONFIRMED but NOT fixed (behaviour change): _is_duplicate_screenshot (line ~588, inside the replay template) sums the concatenated 768-bin RGB histogram as if bins were pixel values – the exact bug validation/compare.py documents and fixed – so the ratio for identical images is ~1.0 and near-duplicate screenshots are never skipped. Fixing it would make Windows replays save fewer screenshots (visible behaviour change) → listed, not changed.
- generator/script_generator.py 1300–2338 (read via filtered copy: comment/blank lines removed, original numbers kept). Locator tiers – no confirmed bugs (CSS-id selectors with special chars raise inside try/except → tier skipped).
- generator/script_generator.py 2338–3744 (read). No confirmed bugs (frame/icon/position tiers; all Playwright calls guarded).
- generator/script_generator.py 3744–5359 (read). Fix #? re-check: ControlOrMeta+A (line 3897) present and correct.
  - CONFIRMED (Mac/Linux): _wait_for_live_otp (~line 5075) deletes otp_input.txt even when it read an EMPTY value. app.py writes the file with write_text (create+truncate, then write); a poll landing between the two reads "" and unlinks the file – on POSIX the delete succeeds and the user's OTP is silently lost (Windows usually refuses to delete a file another process has open). Minimal fix: only unlink after a non-empty read.
- generator/script_generator.py 5359–6598 (read). Earlier fix #4 (_late_nav_not_caused and its two call sites) re-checked in place: correct, no conflict with _next_step_owns_destination.
- generator/script_generator.py 6598–7791 (read). Note: several template-string lines use invalid escape sequences like '\s' / '\d' (raised as SyntaxWarning on Python 3.12 when script_generator is imported; harmless today, would become errors in a future Python). Pre-existing, not OS-specific – listed under Known limits.
- generator/script_generator.py 7792–9175 (read). Click/verify/hover-chain/resolve helpers. No new issues.
- generator/script_generator.py 9176–10218 (read). Readiness/submit/popup/new-tab/chat helpers. No new issues (regex escapes are doubled correctly for the non-raw template).
- generator/script_generator.py 10219–11263 (read). Chat send/stop helpers, state readers. Minor (not fixed, harmless): _chat_fast_locate line ~10689 escapes quotes with '\"' inside the non-raw template, which becomes a no-op in the generated script; a label containing a double quote gives an invalid selector that is caught and skipped (falls through to role/css lookup). No crash; listed only.
- generator/script_generator.py 11264–12375 (read). Checkbox state, polling, drag value/nudge, effect verification, numeric token helpers. No new issues ($$ escapes correct for string.Template).
- generator/script_generator.py 12376–13633 (read). Value-range resolution, locator report, hover-reveal wait, modal diagnostics/paint checks. No new issues.
- generator/script_generator.py 13634–14791 (read). Modal wait/retry, dynamic URL segment matching, URL notes. No new issues.
- generator/script_generator.py 14792–15873 (read). URL classification, settle/visual-settle waits, near-blank PNG check, add-to-cart helper. No new issues.
- generator/script_generator.py 15874–16926 (read; long line 16047 checked in full). Settle, scroll anchors, final target decision, visibility/enabled rules, pinned locator, names, history step. No new issues.
- generator/script_generator.py 16927–18568 (read). Failure composer, resolve_and_act wrapper/core: overlay guard, tier list, final decision/verify loop, click dispatch. Note: _post_click_check returns (True, None) early (line ~17796) – later body is intentionally dead code; not a bug. No new issues.
- generator/script_generator.py 18569–20145 (read). Action dispatch (fill/select/check/drag/hover), force/overlay recovery, scroll-search, fallbacks, bbox click, fill retry, diagnostics, page resolution. No new issues (paths via pathlib).
- generator/script_generator.py 20146–21299 (read). Settle/scroll helpers, block detection, click_if_exists, product validation, timing wrappers, start of run(). RESOLVED earlier TO-VERIFY: run() initialises result['status']='FAIL' (line ~21210), so a run killed before its first step is never reported PASS – not a bug.
- generator/script_generator.py 21300–23326 (read). run(): browser/context setup (template $-placeholders for viewport etc.), new-page registry, step loop prologue, skip paths, page resolution, navigate branch with fallbacks, scroll branch. No new issues.
- generator/script_generator.py 23327–24639 (read). Scroll verify, tab_switch/open/close, validate*, click_if_exists, add_to_cart, capture/compare, screenshot, count*, check_checked, value_range branches. Minor/cosmetic (not fixed): skip branches before line ~22291 (site-popup / hover-unseeable / double-submit / merged-duplicate) write count_summary_rows/value_range_rows/page_mismatch_info carried over from the previous step's iteration; no NameError is possible because step 1 is always a navigate that initialises them. Report-only effect, rare.
- generator/script_generator.py 24640–26150 (read). detect_duplicates/capture_list/compare_list/__validate_xpath__, generic action branch: OTP roles (calls _wait_for_live_otp), frame dispatch, effect verification, modal checks, page-mismatch capture, chat/stop post-checks. No new issues.
- generator/script_generator.py 26151–27352 (read). End of run(): result assembly, not-run backfill, final screenshot, product validation, status calc, close delay, empty-dir cleanup, _write_result (atomic), __main__; module-level test_case_has_otp_step, generate_script (migrate_recording applied; atomic write with .tmp<pid>). generator/script_generator.py DONE (1–27352, no gaps).

## Coverage: 100% of every runtime file (Step 1 complete)

## Step 3 – fixes applied (backups: app.py.bak_fullaudit, generator/script_generator.py.bak_fullaudit)
- F1 generator/script_generator.py:5078-5084 – _wait_for_live_otp deletes otp_input.txt only after a non-empty read.
- F2 generator/script_generator.py:16 + 27333 – generate_script temp file name includes the thread id (watcher thread and run route share one process id).
- F3 app.py:889-895 – _run_recording_session finally: phase still launching/recording/stopping -> "failed" + message.

## Verification of open items
- run() starts with result["status"]="FAIL" -> a killed-early run is never PASS (not a bug).
- generate_script concurrency: confirmed same tmp path for watcher thread + run route (same pid) -> fixed by F2.
- _cleanup_empty_dirs (GET /api/screenshots/sessions etc.) does not skip active replay folders; _write_result does not create the parent folder. Harm only in a narrow chain (screenshots panel opened during replay start-up AND first write is an unwrapped _write_result) -> SUSPECTED, not fixed (would change cleanup behaviour).

## Step 4 – read-only final review
- py_compile: all runtime .py files OK (pre-existing SyntaxWarning '\d' at script_generator.py:1601, present in the backup too).
- SCRIPT_TEMPLATE substituted with dummy values and compiled: OK.
- node --check recorder/action_capture.js, static/js/script.js: OK (unchanged). HTML/CSS files unchanged.
- Backups exist; existing backups/_backup_before_crossplatform untouched.
