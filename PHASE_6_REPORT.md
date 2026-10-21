# Phase 6 Report: Safety and Polish

Date: 14 October 2026. Only Phase 6 was implemented. Nothing was run; the only checks were static (Python parse, `node --check` on the editor's scripts, a Jinja parse, line-ending checks).

## 1. Step 0 findings relevant to this phase

- **Earlier phase reports** 1-5 were read; their work is reused unchanged.
- **Deleting a step** in the Recording Editor (`renderActions()`, the ✕ button) used the browser's `confirm("Delete this action?")` for every step, then pushed the step onto the Undo Delete stack and removed it.
- **OTP steps in a recording:** the recorder marks them `otp_field` (the fill) and `otp_focus` (clicks into it). Older recordings carry no mark. Their field can still be recognised by `autocomplete="one-time-code"`, or by a name / id / placeholder / aria-label naming "otp".
- **Review of Phases 1-5** (see Sections 2 and 3): one real Windows issue, no macOS issue, and no place where a mode was missed. One defect, the Phase 4 doubled line endings, had already been found and fixed in Phase 5.

## 2. What was changed

| File : function | Change | Reason |
|---|---|---|
| `templates/recording_editor.html`: the delete button in `renderActions()`; new `performStepDelete()`, `stepOthersMayDependOn()`, `openDeleteDependsDialog()`; new `#deleteDependsModal` | Deleting a **Navigate, Open Tab, Switch Tab, Capture Value, or OTP step** opens an in-app confirmation (the same `modal-overlay` / `modal-dialog` style as the Pick Element / Add Action dialog): "Later steps may depend on this step. Delete anyway?" with **Cancel** and **Delete**. An OTP step is one the recorder marked, or whose field is `autocomplete="one-time-code"` or names "otp". **Every other deletion is unchanged** (same browser confirm). The deletion itself (Undo Delete stack, step count, re-render) is the same code as before, moved into `performStepDelete()` so both confirmations share it. | Phase 6 requirement. |
| `app.py`: `/api/test/run/pause/answer` | Writing the answer file (`os.replace`) is retried up to 10 times, 50 ms apart, on `PermissionError`. | **Windows defect:** Windows can refuse the rename for a moment while the replay process is reading the file. The same pattern the replay already uses for `report.json`. macOS / Linux never hit the retry. |

## 3. Review results (Phases 1-5, both modes, Windows / macOS)

| Area | Finding | Action |
|---|---|---|
| Paths | Every new path uses `pathlib` (run folder, `stop_request.txt`, `pause_answer.json`, `<report>.alive`, `captured_messages/`, `config/message_keywords.json`). File names contain no `:` or other characters Windows forbids. | none |
| Keyboard keys | No new key combinations. The card inputs only use Enter (the same on both). | none |
| Console output | The new emoji lines ("🔔 Captured …") are safe on Windows consoles: the generated script already switches stdout / stderr to UTF-8 with a replace fallback, and the executor reads them as UTF-8. | none |
| Popups and cards | The live-log window opens with `window.open` inside the click (allowed by popup blockers on both). The cards and modals are plain HTML / CSS (`position: sticky`, flexbox), which render the same in Chrome, Edge and Safari. | none |
| Answer file on Windows | `os.replace` could be refused while the replay reads the file. | fixed (Section 2) |
| Process time limit | `communicate(timeout=…)` retried in a loop works the same on Windows and POSIX (documented subprocess behaviour). | none |
| Line endings | The Phase 4 block's doubled `\r\r\n` endings were fixed in Phase 5. A check of every changed file finds no bare LF in CRLF files, no `\r\r\n` and no lone CR. | already fixed |

**One replay path for both modes (code review).** The only places that look at MODE B are its specified differences:

- the per-step screenshot switch (`_capture_screenshot`);
- the partial-run setup and the stop after step N (`run()`, top of the loop);
- the `fast` flag on results;
- "Could not reach step N" (only after the cards had their chance);
- the end message.

All of the following have **no** mode check, so they run identically in MODE A and MODE B:

- the live-log events and filtering (Phase 1);
- Stop and the active-run lock (Phase 2);
- the pause engine, OTP card and fallback card (Phase 3);
- message capture and the smart wait (Phase 4);
- the field-error card and re-runs (Phase 5).

After a pause, the mode simply continues, because fast mode is decided per step from the selected step number.

## 4. Backup files created (`backups/phase_6/`)

- `backups/phase_6/app.py`
- `backups/phase_6/templates/recording_editor.html`

## 5. Decisions made on my own

1. **An OTP step is recognised in the editor by recorded facts only:** the recorder's `otp_field` / `otp_focus` marks, `autocomplete="one-time-code"`, or "otp" in the field's own name / id / placeholder / aria-label. The editor cannot run the replay's full OTP detection.
2. **Other deletions keep the existing browser confirm**, as required ("Other deletions are unchanged").

## 6. Skipped / not possible

- Nothing else from the Phase 6 list was needed. No other real Windows / macOS difference and no missed mode was found.

## 7. Known limitations

- An OTP step in an older recording whose field shows no OTP sign (no mark, no `one-time-code`, no "otp" in its own attributes) gets the normal delete confirmation.
- The delete confirmation does not check whether later steps really depend on the step; it is shown for these step types.

## 8. Manual test checklist

**New behaviour**

- [ ] In the editor, delete a Navigate, an Open Tab, a Switch Tab, a Capture Value and an OTP step: each shows the in-app "Later steps may depend on this step. Delete anyway?" dialog.
  - Cancel keeps the step.
  - Delete removes it.
  - Undo Delete brings it back in place.
- [ ] Delete a click or fill step: the same browser confirm as before.
- [ ] On Windows: in a run with an OTP or a field-error card, answer the card; it is accepted, with no "Couldn't pass the answer on" message.

**Both modes, end to end**

- [ ] MODE A (Replay): live log in sync, the OTP card, captured messages, the field-error card (Continue / Retry as is / Stop), the fallback card (Retry step / Stop), and the Stop button.
- [ ] MODE B (▶ on step N): the same cards and capture during the ⏩ FAST steps. After each pause the run continues fast to N, runs N normally, then stops with "Stopped after step N (partial run)".

**Existing flows**

- [ ] Recording (start, stop, the rename popup), full replay of an old recording, Pick Element, validations.
- [ ] Live logs, timestamped screenshots, the HTML report, and opening old recordings.
- [ ] Repeat on Windows and macOS.
