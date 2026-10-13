# AutoFlow - Chatbot Reply Wait Fix Report

Date: 13 October 2026

## 1. Root cause (written before any code was changed)

### 1.1 The existing chatbot-wait code

All references are to `generator/script_generator.py` (the replay template) and `recorder/action_capture.js`, before the fix.

**(a) What counts as a chatbot send** - `_chat_is_send_step` (`script_generator.py:10555`) and `_chat_send_proven` (`:10610`):

- The step must be either:
  - Enter (without Shift) in a text-entry element; or
  - a click on a button or submit control right after a fill.
- The recording must also prove a conversation:
  - the box is a conversation editor (`_chat_conversation_editor`, `:10661`: a textarea, a contenteditable element, `role=textbox`, or an input named message / prompt / chat / ask); and
  - either the recorder's facts `message_echoed` and `input_kept` are true, or an older recording shows the same box used again or a stop control.

**(b) When a reply has started** - `_chat_wait_reply_done` (`:10911`), part (a):

- new page text appears (the echoed prompt excluded); or
- the controls beside the input change from the snapshot taken before the send (`_CHAT_FP_JS`, `:10520`).

**(c) When a reply has finished** - `_chat_wait_reply_done`, part (c):

- the new page text has not changed for `CHAT_REPLY_SETTLE_S` = **2 s**; and
- the input area is not in its "busy" state.
- "Busy" is only recognised when the control snapshot differs from the **idle snapshot**. That idle snapshot is taken in `_chat_capture_idle` (`:10697`), called at the fill step **before the text is typed**, so the box is empty at that moment.

**(d) After which steps it waits** - run() (`:26745`):

- after every step that passes (a);
- when the next real step was recorded during the reply, the wait is deferred until before the first later step that was not (`_chat_should_defer` / `_chat_deferred_before_step`).

**Recorder side** - `afqaStartReplyWatch` (`action_capture.js:4531`):

- It starts only when a text box holding text is sent (`action_capture.js:4699`).
- It ends the reply after **2 s** without page changes (`AFQA_REPLY_SETTLE_MS`), using the same idle-fingerprint rule.
- It saves `reply_text`, `message_echoed` and `input_kept`.
- It records **no reply start, end or duration**.

### 1.2 What the recording `session_20261013_094024` stored (steps 9-27)

**The send steps**

| Step | Action | Recorded facts | `reply_text` begins with |
|---|---|---|---|
| 11 | click on the send button (`<button class="control-button send-button">` with an arrow-up icon), after fill step 10 | `message_echoed: true`, `input_kept: true`; `submit.field_cleared` and `content_added` true | "Working Generating response…" |
| 15 | Enter in the textarea | as step 11 | "Reasoning Generating response…" |
| 19 | Enter in the textarea | as step 11 | "Working Making sense of it…" |
| 23 | Enter in the textarea | as step 11 | "Working Refining output…" |
| 26 | Enter in the textarea | as step 11 | "Working Analyzing results…" |

**Other steps**

- Steps 12, 16, 20, 24 and 27 are scrolls recorded with `during_reply: true`.
- Steps 9, 13, 17 and 21 are **clicks on the message textarea**, not suggestion chips.
  - The report calls them "✧˖° Summarize a lead's recent activity…" because that is the nearest text.
  - Their recorded target is `tag: textarea`, and every one is followed by a fill of the same box.
- **No chip click sends a message in this recording.** That part of the question's reading is rejected.

**How long you waited (recorded gaps from a send to the next message)**

- Step 15 → step 18: 0.9 + 26.1 + 25.3 s.
- Step 11 → step 14: 0.8 + 20.1 + 14.5 s.
- You waited 20-26 seconds every time before touching the box again.

**What the reply text shows**

- Every saved `reply_text` is only the bot's **status line** ("Working / Generating response…").
- The recorder's own watch therefore ended the reply after 2 s, while the bot was still preparing its answer.
- No reply start, end or duration was recorded.

### 1.3 What happened in replay (run `…_20261013_095324`; the other two runs are identical)

**Replay log**

- Step 15 (Enter): PASS. Its reply wait is deferred to step 17, because step 16 was recorded during the reply.
- Step 17: "Waiting for the chatbot to finish replying… 6s", then "Waited 6s".
  - Measured from the send, the bot was declared finished about 6 s after step 15's Enter.
  - In the recording, the user waited about 26 s or more.
- Step 18 (fill): PASS. This app allows typing while the bot replies.
- Step 19 (Enter): `[submit-check] FAILED … Pressed Enter in 'field', but nothing was sent (the text is still in the box)`, with replay values `{'cleared': False, 'added': 1}`.
  - This is the result after `_chat_resend_once` (`:11531`), which waited for 2 quiet seconds (`_chat_wait_page_idle`) and pressed Enter again.

**Screenshots**

- `step18_field_show_me_the_leads_from_the_it_indu…png`, taken right before step 19:
  - the bot still shows "**Working** · Making sense of it · **Understanding your request…**" (no answer text yet);
  - the box holds the new message;
  - the send arrow is **greyed out**.
- `step19_field_FAILED…png`, 14 s later:
  - the answer is now **streaming** ("All deals expected to close this month… It appears that the");
  - the new message is still in the box;
  - the send arrow is still greyed out.

So the bot was still replying when step 19 ran. The send control was unavailable, and the Enter reached the box but the app ignored it.

### 1.4 Is the wait attached to the right action?

- **Yes.** The wait follows the step that sent the message:
  - step 11, a send-button click;
  - steps 15, 19, 23 and 26, Enter presses.
- The "chip" steps (13, 17, 21) are clicks into the textarea.
- The waits printed under them are the deferred reply waits of the previous send, which is correct timing.

### 1.5 Is the "message was not sent" check correct?

- **Yes.** The text stayed in the box and the message never appeared in the conversation (`cleared: False`).
- The step really did not send. Even the resend was pressed while the bot was still replying.
- The check is right; the moment it was used was too early.

### 1.6 Root causes

**R1 (replay):** `_chat_wait_reply_done` decides "finished" too early. It needs 2 s of unchanged page text plus the input area out of its busy state, and both parts fail here:

- **The "busy" state can never be detected on this kind of page.**
  - The idle snapshot is taken with an **empty** box. On this page the send arrow is disabled whenever the box is empty, so the busy snapshot (empty box, bot replying) is identical to it.
  - With `busy_fp = None`, only the text rule decides.
- **The 2-second text rule is too weak.**
  - The bot shows a status line ("Understanding your request…") that stays unchanged for many seconds while it prepares the answer. That is a pause inside the reply.
  - Two quiet seconds were taken as "finished" (about 6 s after the send), so steps 18-19 ran while the answer had not even started.

**R2 (replay):** before sending the next message, nothing checks that the box and its send control are ready.

- The real signal was visible: with text in the box, the send arrow was disabled while the bot replied. It is enabled when the bot is idle, as it was at step 11.
- But the replay pressed Enter without looking at it.
- `_chat_resend_once` then waited for the same weak 2-quiet-seconds rule and pressed Enter again into the same busy state.

**R3 (recorder):** `afqaStartReplyWatch` uses the same 2-second rule.

- So the recording ends the reply early (`reply_text` is only the status line).
- It stores no reply start, end or duration, so replay cannot size its waiting from the recording.

**Your reading: "the wait decides finished too early, so step 19's Enter was pressed while the bot was still replying and the app ignored it."**

- **Confirmed**, with the evidence above. The early signal is the 2 s quiet period together with a busy check that cannot see this page's busy state.
- **Rejected:** "a chip click sends the message" does not apply to this recording.

## 2. How chatbot sends are detected now, and how "reply finished" is decided

### 2.1 Which steps count as chatbot sends

**The detection rule is unchanged** (`_chat_is_send_step` / `_chat_send_proven`).

- The section 4 check shows that it already selects exactly the chat sends, and nothing else, in every recording.
- Keeping it unchanged is what guarantees that normal inputs get no extra waiting.

**New recordings** additionally carry facts the recorder actually observed:

- `reply_observed: true`, set only when page content outside the box started changing within 3 s of the send;
- `reply_started_ms`;
- `reply_duration_ms`.

### 2.2 When the reply counts as finished

**The ready state.** When a chat message is sent successfully, the replay remembers how the area around the message box looked right before that send, with the text typed in. This is the **ready state**. It records:

- whether the box is editable;
- for each control beside the box: its name, icon, whether it can be used (`disabled`, `aria-disabled`, `pointer-events: none` or a not-allowed cursor) and its class;
- whether an `aria-busy` marker is present.

**Before the next message from the same box is sent** (after its text is typed), the replay waits until that area is back in the ready state:

- the box is editable;
- every control that was usable then is present again, with the same name and icon, usable and with the same class;
- no new `aria-busy` marker is present.

**Why this is a real "finished" signal**

- While a chatbot replies, its send control is disabled, greyed or replaced by a stop button, or the box is disabled. That is why the app ignored step 19's Enter.
- A status line that stands still for many seconds no longer counts as finished.
- The existing after-send wait (text still for 2 s, busy state) is kept, so screenshots and comparisons still happen at the same moment as before.

**Bounds**

- The maximum wait is counted from the previous send.
- It is 3 × the recorded reply duration (at least 60 s, at most `CHAT_REPLY_MAX_S` = 180 s). With no recorded duration, which is the case for every older recording, it is `CHAT_REPLY_MAX_S`.
- It is a bound only. There is no fixed sleep: the condition is checked every 250 ms.

**If the maximum is reached**

- A warning is shown: "The chatbot was still replying Xs after the previous message (the message box and its send control did not become ready). Sending anyway."
- The send is still made and checked, so a message that is not sent still fails.

**The automatic resend** (`_chat_resend_once`) also waits for the ready state, not only for quiet text.

**Older recordings**

- The ready state is learned during the replay itself, from the first message that was sent successfully.
- So `session_20261013_094024` is covered without re-recording: step 11 teaches it, and steps 15, 19, 23 and 26 wait for it.

## 3. Fixes

### 3.1 Changes

Backups made before editing:

- `generator/script_generator.py.bak_chatbotwait`
- `recorder/action_capture.js.bak_chatbotwait`
- `recorder/record_session.py.bak_chatbotwait`

Lines marked "template" are inside `SCRIPT_TEMPLATE`, so they reach every generated script.

| # | File:line | Problem | Change |
|---|---|---|---|
| C1 | `generator/script_generator.py:10714` (`_CHAT_READY_JS`), `:10736` (`_chat_ready_now`), `:10748` (`_chat_controls_ready`), `:10780` (`_chat_wait_send_ready`), template | The next message was sent while the bot was still replying (R1, R2) | New ready check, reusing `_CHAT_STATE`, `_resolve_element`, `_same_field_steps`, `_url_note_log` and the existing control-area logic of `_CHAT_FP_JS`. |
| C2 | `generator/script_generator.py:23115` (before `_chat_prepare_send`), template | The check had to run right before a chat send | Calls `_chat_wait_send_ready` only for steps already detected as chat sends. |
| C3 | `generator/script_generator.py:26873` (after a successful send), template | The ready state had to be learned | Stores the pre-send state of the area as the ready state for that box. |
| C4 | `generator/script_generator.py:11651` (`_chat_resend_once`), template | The resend used the same weak quiet-text rule (R2) | Also waits for the ready state before resending. |
| C5 | `generator/script_generator.py:10768` (`_chat_reply_max_s`), `:11059`, template; `:27911` (`generate_script`) | No recorded reply time to size the limits | The bounds come from the recorded duration (3×, at least 60 s, at most 180 s); with none, 180 s as before. The new fields are passed through to the generated script. |
| C6 | `recorder/action_capture.js:4550`-`:4577` (`afqaStartReplyWatch`) | The recording had no reply start, end or duration (R3) | A second observer measures the first and last page change outside the box until the user's next own action. It sends `reply_observed`, `reply_started_ms` and `reply_duration_ms`, only when a reply started within 3 s. |
| C7 | `recorder/record_session.py:511`-`:527` (`_apply_reply_patch`) | The new facts had to be stored on the step | Accepts the new fields. A pending patch now merges into earlier ones instead of replacing them. |

### 3.2 Generic rule per change, and why it is safe

- **C1:** "The next chat message is sent only when the area around its message box looks again like it did when the previous message was sent successfully."
  - Any chatbot shows that it is busy in the controls next to its box: disabled, greyed, stop button or locked box.
  - Safe: unreadable means not blocking. It runs only for chat sends, and it is bounded, with a plain-English warning.
- **C2:** "The ready check runs only for steps already detected as chat sends."
  - The detection is unchanged, so normal inputs never reach it.
- **C3:** "A state is ready once a message was really sent from it."
  - It is learned during the replay, so it fits any site.
  - It is only kept for the same box.
- **C4:** "A resend waits for the same ready state."
  - It only adds a condition to a path that already ran only for failed chat sends.
- **C5:** "Recorded reply time only sizes the maximum wait."
  - There is no sleep, and old recordings keep the 180 s bound.
- **C6:** "A reply is recorded only when the page changed right after the send."
  - It runs only inside the existing reply watch, which only starts for a conversation box holding text.
  - Other fields are recorded exactly as before.
- **C7:** These are optional fields; old code ignores them.

**Windows and macOS**

- Everything is DOM and computed-style reads through Playwright, with `wait_for_timeout` polling.
- There are no keyboard or OS differences, and no file paths.

## 4. All-recordings check

`_chat_is_send_step` was run over all 65 recordings, including `edited/`, with the exact step list `generate_script` builds.

**Recordings with chat sends**

| Recording | Site | Chat send steps |
|---|---|---|
| `session_20261006_185202` | chatgpt.com | 5, 8 (Enter); 11, 15, 21 (send click) |
| `session_20261006_185327` | chatgpt.com | 5, 9, 14 (click) |
| `session_20261006_185600` | chatgpt.com | 3, 9, 13, 17, 22 (click) |
| `session_20261006_225609` | chatgpt.com | 3 (Enter); 8, 13, 18 (click) |
| `session_20261006_234503` | chatgpt.com | 3 (Enter); 6, 11, 15 (click) |
| `session_20261007_111714` | techdemo.delveant.cloud | 20, 25, 35 (click); 30, 39 (Enter) |
| `session_20261009_110615` | techdemo.delveant.cloud | 18, 25, 33 (click); 22, 29 (Enter) |
| `session_20261013_093507` | chatgpt.com | 4, 8, 13 (click) |
| `session_20261013_093734` | chatgpt.com | 4 (Enter) |
| `session_20261013_094024` | techdemo.delveant.cloud | 11 (click); 15, 19, 23, 26 (Enter) |

**Totals**

- 40 steps, all chatbot conversations.
- **No** login, search, signup, registration, OTP, pincode or other form steps are included.
- Every other recording has none, for example:
  - Sportzia signup and OTP;
  - Coimbatore marathon registration;
  - Myntra search;
  - the e-commerce and login flows.
- Those steps never reach the ready check, so they get no extra waiting.

**Generated scripts (not run)**

- Generated and compiled:
  - `session_20261013_094024` (the failing chatbot recording);
  - `session_20261013_093507` (ChatGPT);
  - `session_20261009_152733` (registration form);
  - `session_20261012_105745` (signup + OTP);
  - `session_20261007_153501` (Myntra).
- All compile.
- In the non-chatbot recordings the new code exists but is never reached, because no step there passes `_chat_is_send_step`.

**Unit check of the ready comparison: 8 out of 8 correct**

| Case | Result |
|---|---|
| same state | ready |
| send disabled | not ready |
| greyed by class only | not ready |
| replaced by a stop button | not ready |
| box disabled | not ready |
| `aria-busy` present | not ready |
| an extra new button, send control usable | ready |
| unreadable | does not block |

**Other checks**

- `py_compile`: OK.
- `node --check action_capture.js`: OK.
- The template substitutes and compiles.
- No new backslashes or `$` in the template.
- CRLF is kept in all three files.

## 5. Not fixed (needs a decision or could not be proven)

- **A suggestion chip that sends a message.**
  - No recording contains one; steps 13, 17 and 21 here are textarea clicks.
  - Detecting chip sends would change the unchanged chat-send detection and could not be verified, so it was not added.
  - Recorder support for it (start the reply watch on a click when the page has a conversation box) is the natural next step if you want it.
- **The after-send wait itself is unchanged** (2 s of still text plus busy state), apart from its bound.
  - Steps that come right after a reply but are not sends (for example a click on something in the answer) can still run before the answer has fully finished.
  - The message box is empty during the reply, so the ready state cannot be judged then.
  - A stronger signal (for example new running CSS animations) is possible but unproven.
- **Network streaming signals are not used.**
  - The existing code deliberately never lets requests or sockets block, because many pages keep connections open permanently.
  - This was left as is.
- **The recorder's reply text is still read with the 2 s rule** (unchanged, so `during_reply` flags stay as they are).
  - The new duration field is measured separately and is not affected by it.

## 6. Test checklist (in order; Windows and macOS)

1. Replay `session_20261013_094024`:
   - step 19 shows "Waiting for the chatbot to finish replying before sending the next message… Ns", then "finished replying …";
   - steps 19-32 pass, with the same behaviour at steps 23 and 26.
2. Record a fresh chatbot conversation with 3 or more messages:
   - the JSON has `reply_observed`, `reply_started_ms` and `reply_duration_ms` on each send;
   - replay passes.
3. A chatbot with long or slow replies: the replay waits for the whole answer before sending the next message, with no timeout warning.
4. A chatbot where a suggestion chip sends the message: currently no new behaviour (see section 5). Confirm nothing regressed.
5. A chatbot that uses a send button instead of Enter (`session_20261013_093507`, ChatGPT).
6. A normal login form and a search box with Enter: no "Waiting for the chatbot" lines, and step times unchanged.
7. A signup or registration form (`session_20261009_152733`): unchanged.

## 7. Rollback

```
cp generator/script_generator.py.bak_chatbotwait generator/script_generator.py
cp recorder/action_capture.js.bak_chatbotwait recorder/action_capture.js
cp recorder/record_session.py.bak_chatbotwait recorder/record_session.py
```

On Windows, use `copy /Y` with the same names.

Recordings made after the fix carry only optional extra fields, which the old code ignores.
