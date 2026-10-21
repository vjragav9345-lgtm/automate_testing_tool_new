# FEATURE: Pick Element on Recorded Page Snapshots (No Replay)

Date: 15 October 2026. The reports and the actual code were read first: the recorder, Pick Element and its overlay, drag-select and XPath generation, replay, the editor and the executor.

Nothing was run: no app, recording, replay or tests. The checks were static:
- Python compile of every changed file;
- compile of a generated replay script from the template;
- `node --check` of `action_capture.js`, of the new 1-of-1 page script and of the editor's inline script;
- a Jinja parse;
- line-ending checks;
- a functional check of the new snapshot helpers on a synthetic MHTML archive (masking, script neutralising, archive serving, step mapping; temporary files removed).

## 1. Step 0 findings

### Recorder

- **Where it runs.** `app.py → _run_recording_session()` runs on its own thread, which owns the Playwright browser (headed Chromium, `pw.chromium.launch`).
- **How it captures steps.** `recorder/record_session.py → Recorder`:
  - `install_context_capture()` registers the context-level `recordAction` binding plus `action_capture.js` as an init script.
  - Page events reach `Recorder._on_action()` → `_record()`.
  - Navigations come in through `framenavigated` (`_on_navigate`).
  - These callbacks run inside Playwright's own dispatch, so a blocking Playwright call there deadlocks (also documented in `pick_element.py`).
- **The polling loop.** The session loop (0.5 s, `probe_page.wait_for_function("1")`, `enter_pressed.wait(0.5)`) is the safe place for any extra page work.
- **Saving.**
  - During recording: `_flush_draft()` writes `storage/recordings/session_<ts>.json` plus a `.jsonl` sidecar.
  - On stop: `_finish_recording()` → `recorder.stop(name=<draft stem>)` → `repository.save_recording()` to `storage/recordings/<name>.json`.
- **Rename and delete.**
  - Rename (`repository.set_display_name`) only changes `display_name`; the file name and `name` never change.
  - Delete: `/api/recordings/delete` → `storage/session_files.delete_session(name)`.
- **Existing snapshot folder.** `storage/snapshots/` already existed: `_capture_dom_snapshot()` keeps gzipped HTML of navigations under a uuid folder. That is unchanged.

### Pick Element (`recorder/pick_element.py`, `app.py`, `templates/recording_editor.html`)

- **Entry points.** All four use the same Add Action modal, the same button and the same `insert_after_index`:

| Modal | `insert_after_index` |
|---|---|
| Edit Step N | N-2 (0-based index − 1) |
| Add Action Before Step N | N-2 |
| Add Action After Step N | N-1 (or the following tab_open) |
| Add Action at the end | last |

- **How it reaches the page today.**
  - `/api/recordings/pick_element/start` → `_slice_preceding_actions()` → `start_pick_session()`.
  - That replays the steps up to the insertion point (`_replay_preceding_actions` with `resolve_and_act` loaded from a generated script), in a fresh browser (`_run_pick_session_fresh`) or a warm one (`_WarmPickSession`).
  - Opening the modal also calls `/pick_element/prewarm`, which **starts that replay in advance**.
- **Overlay.** `_run_pick_wait_phase() → _inject_pick_mode()` exposes `pickResult` / `pickReleased` and injects `window.__afqaPickMode = true` + `_CAPTURE_JS` (`action_capture.js`):
  - the pink overlay and highlight (`_afqaSetupPickOverlay`: `#ff4081`);
  - click-to-lock and double-click-to-release (`lockPick` / `releasePick`);
  - drag-to-select (`_afqaHandleDragSelection`, `mode: "multi"`).
- **XPath generation and return.**
  - XPath: `buildLocatorProfile()` → `xPath()`, plus `buildXpathCandidates()`.
  - The match count is computed in the page (`match_count`).
  - The result goes back through `_PICK_RESULTS` → `/pick_element/status` → the editor's `applyPickedProfile()` ("Found: N of N").

### Replay and step references

- **Replay** is the generated script from `SCRIPT_TEMPLATE`, run as a subprocess (`executor/run_execution.py → start_replay`, `_replay_env`).
- **The stable step reference** (Phase 1, `app.py → _step_ref`) is the recorded step's own timestamp, else `"<index>:<action type>"`.

## 2. Changes made

| File : function | Change | Why |
|---|---|---|
| **new** `recorder/page_snapshot.py` | Shared snapshot code: <ul><li>names and references (`safe_name`, `snapshot_dir`, `step_ref`, `recording_names`, `target_ref`, `find_snapshot`, `has_snapshot`, `delete_snapshots`);</li><li>a minimal byte-preserving MHTML reader;</li><li>masking (`mask_mhtml`);</li><li>capture (`capture_page`: `Page.captureSnapshot {format: "mhtml"}` through `context.new_cdp_session(page)`);</li><li>`save_missing_step_snapshot`;</li><li>`RecordingSnapshotter` (tick / capture_final / finalize);</li><li>opening (`load_archive`, `open_snapshot_page`).</li></ul> | Tasks 1-3 |
| `app.py → _run_recording_session` | Creates a `RecordingSnapshotter` after `recorder.start()`. Calls `tick()` in the existing polling loop, and `capture_final()` when the user stops (browser still open). Errors only switch snapshots off. | Task 1 |
| `app.py → _finish_recording` | New optional `snapshotter`. After the recording is saved, `finalize(actions)` assigns the snapshots to the saved steps. | Task 1 |
| `app.py`: new `_pick_snapshot_for()`; `/pick_element/start`, `/pick_element/prewarm` | Finds the snapshot for the insertion point. Start passes it on (plus where to save a missing one). Prewarm does **not** replay in advance when a snapshot covers the point. | Tasks 2, 3 |
| `recorder/pick_element.py → start_pick_session`, `cancel_active_pick` | Optional `snapshot` / `snapshot_target`. With a snapshot: the new snapshot session runs, and a newer pick or Cancel ends it. Without one: the existing paths, unchanged. | Task 2 |
| `recorder/pick_element.py`: new `_run_pick_session_snapshot`, `_SnapshotOverlayError` | Opens the snapshot in its own Chromium window (recorded viewport, `bypass_csp`, service workers blocked), restores the scroll, then runs the **existing** `_run_pick_wait_phase`. If anything fails before the picker is live, the window closes and the existing replay-based picker runs (warm session when the editor tab has one), with a note. | Tasks 2, 3 |
| `recorder/pick_element.py → _run_pick_wait_phase` | Optional `extra` (fields added to every status: `pick_source`, `pick_note`) and `snapshot_mode` (the overlay must be live within 5 s, otherwise fall back). New 1-of-1 XPath check after each single-element lock, run in the loop's existing non-reentrant place. | Tasks 2, 4 |
| `recorder/pick_element.py`: new `_XPATH_CHECK_JS`, `_apply_xpath_check` | The uniqueness check and refinement (Section 3). | Task 4 |
| `recorder/pick_element.py → _run_pick_session_fresh`, `_WarmPickSession._do_start_pick`; new `_save_snapshot_after_walk` | After the existing replay walk reaches the step cleanly (no failure or mismatch, recorded URL), the missing snapshot is saved. The fallback note is passed through. | Task 3 |
| `recorder/action_capture.js` (pick mode only) | One read-only getter, `window.__afqaPickLockedElement()` (the locked element). The overlay, selection, drag-select and XPath generation are unchanged; recording mode never defines it. | Task 4 |
| `templates/recording_editor.html` | <ul><li>"Found: 1 of 1 ✓" when the check confirmed it;</li><li>note lines (refined XPath and rule; verified on snapshot; numbered matches; shadow DOM; frame path; check error);</li><li>the source note (snapshot, or replay with the reason);</li><li>`xpath_verified_on_snapshot` / `frame_path` saved in the step's `locator_profile` only while the XPath field still holds the picked XPath (kept on an unchanged edit).</li></ul> | Tasks 4, 5 |
| `generator/script_generator.py` (template): new `_replay_snapshot_saver`, `_save_missing_snapshot_before_step`, `_snapshot_xpath_live_check`; two calls in `run()` | MODE A, not fast: before a step without a snapshot, it is saved (same module and rules). Before a step whose XPath was verified on a snapshot: one live-log line with the live match count. Neither changes a locator, step or run result. | Tasks 3, 5 |
| `executor/run_execution.py → _replay_env`, `start_replay` | For a full replay only: `AUTOFLOW_SNAPSHOT_RECORDING` (the recording name) and `AUTOFLOW_PROJECT_ROOT`. | Task 3 |
| `storage/session_files.py → delete_session` | Also removes `storage/snapshots/<name>/`. | Task 1 |

## 3. How it works

### Saving during recording (Task 1)

- **When snapshots are taken.** The recorder is passive: a recorded step has already happened when Python hears about it, so nothing can run "before" it in the strict sense. After each recorded step the active page is therefore watched for 8 s, from the recording loop's own thread.
  - Every time its DOM signature changes (address, element count, markup length, title), the page is captured again.
  - Only the two latest captures of that quiet period are kept.
  - The last capture taken completely before the next step is that step's "before" page, which is the page the user saw when acting.
  - When the user stops, the final page is captured too.
- **Assignment.** `finalize()` assigns, by time, each saved step the latest capture finished before its timestamp and after the previous step's, and the final page. Unused captures are deleted.
- **De-duplication.** An unchanged page (same address and DOM signature) is not written again; its metadata points at the earlier file.
- **Storage:**
  - `storage/snapshots/<recording name>/<step reference>.mhtml` plus `<step reference>.json` (url, viewport, scroll, captured / saved time, step reference, file, page id, source);
  - `final.mhtml` / `final.json`;
  - file names are made safe for Windows and macOS (`pathlib`, atomic writes).
- **Masking.** The **saved** content is changed, never the live page. In every HTML part of the archive, inputs that are any of the following lose their `value`:
  - `type=password`;
  - `autocomplete=one-time-code`;
  - named or labelled otp / passcode / pin / 2fa / one-time / verification code;
  - single-character boxes (maxlength 1);
  - numeric with maxlength 4-8.

  Only the changed parts are re-encoded (base64); every other byte is kept.
- **Safety limits:**
  - one capture slower than 8 s, or the 600 MB per-recording budget, turns snapshots off for that recording (a warning);
  - a single page over 40 MB is skipped;
  - any error is a warning only;
  - snapshot contents are never logged.
- **Rename / delete.** Rename keeps the link (the folder uses the recording's unchanging `name`). Delete removes the folder. An editor copy (`<name>_edited`) also finds the original's snapshots.

### Choosing and opening a snapshot (Task 2)

- **Which snapshot.** The insertion point K gives the page **before step K+2** (1-based), or `final` after the last step, exactly the page the replay-based picker reaches:

| Purpose | Snapshot |
|---|---|
| Editing step N | before step N |
| Add After Step N | before step N+1, or final |
| Add Before Step N | before step N |
| Add at end | final |

- **Opening.** A separate Chromium window, with the recorded viewport and scroll.
- **The website's scripts never run:**
  - the archive's HTML is served **at its original address** by Playwright request routing (`context.route` + `route.fulfill`), and every resource (CSS, images, fonts, frames) comes from the archive;
  - **every other request is aborted, and script requests always**, so there is no network;
  - in the archive's HTML every `<script>` gets a non-executable type (the element stays, so DOM positions and XPaths are unchanged);
  - inline `on…` handlers are renamed, meta refreshes and `javascript:` frame sources are disabled, and `cid:` frames are served from the archive.
- **Why this approach.**
  - Opening the `.mhtml` file directly was not used: Chromium loads MHTML documents sandboxed (scripts off), and that could also stop the injected overlay's event handlers. This could not be confirmed without running.
  - The routed document is an ordinary page, so the **existing** wait phase injects the **existing** overlay exactly as on a live page: pink box, lock / release, drag-to-select, the same result returned to the editor.
- **Fail-safe.** A missing or unreadable snapshot, a page that does not open, or an overlay that does not start within 5 s: the window closes and the replay-based picker runs, with the note "The page saved during recording could not be opened for this step (…) - replaying the recording up to it instead."

### Fallbacks (Task 3)

- **(a) "Use current page" with the replay browser: not possible without changing replay.** Replay runs in a separate subprocess whose browser exposes no connection to the server.
  - The existing **warm picker session** already uses its open picker browser when it is on that point.
  - Prewarm is now skipped when a snapshot exists, so no advance replay happens then.
- **(b)** Otherwise, the existing replay-based picker exactly as today. When its walk reaches the step cleanly, the missing snapshot is saved for next time.
- **Full replays** (MODE A only, never fast mode or MODE B): before a step that has no snapshot yet, one is saved (once per recording). Fail-safe; it never changes the result.

### 1-of-1 XPath (Task 4)

- **The count.** After each single-element lock (drag-select multi-picks excluded), the existing generator's XPath is counted with `document.evaluate(…, ORDERED_NODE_SNAPSHOT_TYPE)` in the picked element's whole document, hidden elements included.
  - Exactly 1, and it is the picked element: kept unchanged ("1 of 1 ✓").
  - Otherwise a unique relative XPath is built for the picked element. The first candidate that matches only it wins.
- **Candidate order:**
  1. test attributes;
  2. a stable id;
  3. name;
  4. aria-label, placeholder, title;
  5. tag or role + exact `normalize-space()` text;
  6. a linked label (via `for`, wrapping, or following);
  7. href;
  8. any of these under the nearest ancestor with a stable unique attribute;
  9. an index within that ancestor (`(…)[k]`).
- **Rules for values and text:**
  - generated-looking values are skipped (long numbers, UUIDs, hash-like tokens, framework ids such as `css-…`, `:r1:`, `ember…`);
  - texts are quoted with `concat()`;
  - SVG / non-HTML elements use `local-name()`;
  - never `/html/…`.
- **Result.** The refined XPath is returned and the generator's own stays among the candidates.
- **Unknown element.** If the picked element is no longer known, all matches are numbered on the page in the existing pink highlight style, and the editor asks the user to click the intended one. That re-pick then builds the version for it.
- **Frames and shadow DOM.**
  - Frames: the frame path (stable attribute or index) is returned and saved with the XPath. Replay uses its existing frame fallback.
  - Shadow DOM: the editor says an XPath cannot reach the element and the existing locator is used.
- **Scope.** The check also runs in the replay-based picker (it is the same wait phase).

### Live confirmation (Task 5)

- A step whose `locator_profile.xpath_verified_on_snapshot` is set logs, before its action:
  - "Step N: XPath confirmed live: 1 of 1"; or
  - "WARNING - the XPath picked on the page snapshot matched X elements on the live page (expected 1 of 1). The step runs as usual."
- Once per step and run, in every mode.
- When it finds 0 at first it waits up to 3 s for the page to render.
- Nothing about the locator or the result changes.

## 4. Backups (`backups/feature_pick_snapshot/`)

- `app.py`
- `recorder/pick_element.py`
- `recorder/action_capture.js`
- `templates/recording_editor.html`
- `generator/script_generator.py`
- `executor/run_execution.py`
- `storage/session_files.py`

New file: `recorder/page_snapshot.py`. Recording code (`record_session.py`) was **not** changed.

## 5. Decisions made on my own

1. **"Before step N" = the last settled page before the user acted.** It is captured after the previous step, because the passive recorder cannot run anything before a step happens.
2. **Archive served by routing at the original address with scripts neutralised,** instead of opening the `.mhtml` file directly. Only documented Playwright APIs are used, and the existing overlay runs unchanged.
3. **Snapshot saving lives in the recording loop** (`app.py`), not in the recorder's callbacks. A Playwright call inside a callback deadlocks, and the recorder must stay unchanged.
4. **An XPath matching exactly one element that is NOT the picked one is refined.** "Exactly 1" is only accepted when it is the picked element.
5. **The 1-of-1 check also runs in the replay-based picker.** It is the same wait phase.
6. **Prewarm is skipped when a snapshot exists.** This avoids replaying sign-up / OTP steps in the background.
7. **Task 3a is covered by the existing warm session.** The separate replay subprocess cannot be attached to without changing replay.
8. **Masked inputs include single-character boxes and numeric 4-8 maxlength fields.** A blank value there is harmless for picking.
9. **The live confirmation waits up to 3 s when it finds 0 elements.** This avoids false warnings while a page renders.

## 6. Limitations

- **Hover-only elements:** content shown only on hover (`:hover` styles, hover menus not in the DOM at capture time) is not in the snapshot.
- **Fast steps:** a step made less than about 0.5 s after the previous one may have no "before" snapshot (the picker replays instead).
- **Before step 1:** there is no snapshot of the page before step 1 (the initial navigation).
- **Shadow DOM:** XPath cannot reach it; closed shadow roots and canvas content cannot be picked meaningfully.
- **Styles and scroll:** styles that exist only in the CSSOM, and the scroll position of inner scroll containers, may differ from the live page.
- **Pages that change after recording:** the snapshot shows the recorded page. The next replay's live confirmation warns when the XPath no longer matches 1 of 1.
- **Disk space:** about one page file per changed step (capped at 600 MB per recording, 40 MB per page). Old recordings get snapshots through Pick Element replays and MODE A runs, which spend a little time once per missing step.
- **CDP support:** `Page.captureSnapshot` is an experimental CDP method. If the browser does not provide it, snapshots are simply not created and everything works as before.
- **Not verified by running:** none of this was run (as instructed). The MHTML handling was checked on a synthetic archive only.

## 7. Manual test checklist

- [ ] New recording: `storage/snapshots/<recording>/` gets a `.mhtml` + `.json` for the steps, plus `final.*`. Recording behaves and feels exactly as before.
- [ ] Pick Element on a step deep inside a sign-up / OTP flow: the correct page opens at once, with no replay, no sign-up and no OTP. The editor says the page was saved during recording.
- [ ] Pink bounding box, click-to-lock, double-click release and drag-to-select work exactly as before on the snapshot.
- [ ] "Add Action After Step N" shows the page after step N; "Edit Step N" shows the page before step N.
- [ ] An element with hidden duplicates (the same text in desktop and mobile menus): the returned XPath shows "Found: 1 of 1 ✓", and a note says it was made unique.
- [ ] An element with only dynamic ids: the XPath avoids them and is still 1 of 1.
- [ ] An old recording without snapshots: the existing replay-based Pick Element works and creates the snapshot; the next Pick Element there opens instantly.
- [ ] A full replay (MODE A) of an old recording creates the missing snapshots; MODE B / fast mode does not.
- [ ] The next replay logs "XPath confirmed live: 1 of 1" for a picked step (or the warning with the count).
- [ ] Password and OTP values are not present in saved `.mhtml` files.
- [ ] Deleting a recording removes its snapshots folder; renaming keeps Pick Element using its snapshots.
- [ ] Existing flows unchanged: recording, full replay, Run Until, OTP card, field-error card, live logs, screenshots, the rename popup.
- [ ] Repeat on Windows and macOS.
