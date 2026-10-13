# AutoFlow QA

A Flask + Playwright **record-and-replay** browser automation tool. You
launch a real website, perform actions in a real Chromium window, and every
click/fill/scroll/navigation gets captured to JSON. That JSON can be
replayed as-is — or opened in a built-in editor, modified/deleted/added/
reordered, and saved as a new recording — against any target URL (typically
a QA/staging environment), producing a self-contained HTML pass/fail report
with embedded screenshots.

This README describes **only what the current source code in this project
actually does**. It does not describe planned features, older designs, or
anything not present in the code below.

**Technologies actually used:** Python, Flask, Playwright (Chromium, sync
API), Pillow (screenshot diffing), Jinja2 (HTML report templating). There is
no Selenium anywhere in this project.

---

## Table of Contents

1. [Project Structure](#project-structure)
2. [Prerequisites](#prerequisites)
3. [Windows Setup (Step by Step)](#windows-setup-step-by-step)
4. [Running the App](#running-the-app)
5. [Recording Flow](#recording-flow)
6. [Real Recording Example](#real-recording-example)
7. [Where Recordings Are Saved](#where-recordings-are-saved)
8. [Supported Action Types](#supported-action-types)
9. [Locator / Selector System](#locator--selector-system)
10. [Dashboard: Viewing and Editing a Recording](#dashboard-viewing-and-editing-a-recording)
11. [Generated Script](#generated-script)
12. [QA Replay Flow](#qa-replay-flow)
13. [QA URL Mapping](#qa-url-mapping)
14. [Screenshot Storage](#screenshot-storage)
15. [Execution JSON](#execution-json)
16. [HTML Report](#html-report)
17. [Screenshot Comparison](#screenshot-comparison)
18. [Database Status](#database-status)
19. [Retention / Cleanup](#retention--cleanup)
20. [API Reference](#api-reference)
21. [Full End-to-End Example](#full-end-to-end-example)
22. [Exact File Path Table](#exact-file-path-table)
23. [Troubleshooting](#troubleshooting)
24. [Current Limitations](#current-limitations)
25. [Existing Runtime Data](#existing-runtime-data)
26. [Clean Run vs. Keeping Existing Data](#clean-run-vs-keeping-existing-data)

---

## Project Structure

```
new_test/
├── app.py                       # Flask entry point - run this file directly
├── requirements.txt              # Flask, Playwright, Pillow, Jinja2
├── utils.py                      # normalize_url(), attach_dialog_handler()
│
├── recorder/
│   ├── record_session.py         # Recorder class - captures actions on a live page
│   ├── action_capture.js         # Injected into the page to listen for DOM events
│   └── pick_element.py           # "Pick Element" - click-to-fill a locator in the Add Action dialog
│
├── generator/
│   └── script_generator.py       # Turns a recording JSON into a standalone .py script
│
├── executor/
│   └── run_execution.py          # Runs a generated script as a subprocess, builds the result
│
├── validation/
│   ├── compare.py                # Pixel-diff screenshot comparison
│   └── report_generator.py       # Renders the self-contained HTML report
│
├── storage/
│   ├── repository.py             # The only module that reads/writes JSON on disk
│   ├── retention.py               # Age-based cleanup sweep (see "Retention / Cleanup")
│   ├── recordings/                # Saved recordings (session_*.json, + edited/, trimmed/)
│   ├── executions/                # Legacy, unused - see "Current Limitations"
│   └── searches/                  # Legacy, unused - see "Current Limitations"
│
├── templates/
│   ├── index.html                 # Dashboard page
│   ├── recording_editor.html      # View/Edit screen for one recording
│   ├── recording_trim.html        # Trim screen for one recording
│   ├── run_stages.html            # Screenshot Stages viewer for one run
│   ├── screenshots_viewer.html    # Dashboard-level viewer listing every past run
│   └── report.html                # HTML report template
│
├── static/
│   ├── js/script.js              # Dashboard JS (launch/stop recording, list recordings, Replay + live progress)
│   └── css/style.css             # All styling
│
├── generated_scripts/            # Standalone Playwright scripts, one per recording
│   ├── edited/                    # Scripts generated from edited recordings
│   └── screenshoots/              # Per-run screenshots + report.json/report.html (note: "screenshoots" is the real directory name)
├── screenshots/                  # One folder per recording session, launch screenshot only
└── reports/                      # Legacy, unused - see "Current Limitations"
```

`generated_scripts/`, `screenshots/`, `reports/`, and everything under
`storage/` are **runtime output directories** — they are created and filled
in automatically the first time you record something or run a test. They
are not part of the source code you need to set up.

---

## Prerequisites

Verified directly from `requirements.txt` and the project's `venv`:

| Requirement | Version actually used |
|---|---|
| Python | 3.12.7 (the bundled `venv` was built with this) |
| Flask | 3.0.3 |
| Playwright | 1.47.0 |
| Pillow | 10.4.0 |
| Jinja2 | 3.1.6 |
| Browser engine | Chromium only (via `playwright install chromium`) |
| OS | Built and tested on Windows |

**About the `venv/` folder already in this project:** it is a real, working
virtual environment, but it was built on a specific machine and its
activation scripts hard-code that machine's Python install path. Virtual
environments are not portable between machines. **Create a fresh virtual
environment on your machine** (Step 5 below) rather than trying to reuse
the bundled one — the bundled `venv/` folder can be safely deleted, or just
ignored.

---

## Windows Setup (Step by Step)

### STEP 1 — Extract the project

Extract the ZIP anywhere, e.g. `D:\new_test`.

### STEP 2 — Open the project in VS Code

Open VS Code → `File > Open Folder...` → select the extracted `new_test`
folder.

### STEP 3 — Open the VS Code terminal

`` Terminal > New Terminal `` (or `` Ctrl+` ``). Make sure it's a PowerShell
or Command Prompt terminal, and that its working directory is the project
root (it should show something like `PS D:\new_test>`).

### STEP 4 — Verify Python

```powershell
python --version
```
Expected output: `Python 3.12.x` (any modern Python 3 works; the project
was built against 3.12.7). If this errors with "not recognized", install
Python from python.org and make sure "Add Python to PATH" was checked
during install.

### STEP 5 — Create a virtual environment

The ZIP already contains a `venv/` folder, but it's tied to the machine it
was built on and won't work correctly on yours — remove it first, then
create a fresh one:

```powershell
Remove-Item -Recurse -Force venv
python -m venv venv
```
No output on success — a new `venv` folder will appear in the file
explorer.

### STEP 6 — Activate the virtual environment

```powershell
venv\Scripts\activate
```
Your prompt should now start with `(venv)`, e.g. `(venv) PS D:\new_test>`.
Every command after this point must be run with the venv active.

### STEP 7 — Install dependencies

```powershell
pip install -r requirements.txt
```
Expected: pip downloads and installs Flask, Playwright, Pillow, Jinja2 (and
their own dependencies), ending with `Successfully installed ...`.

### STEP 8 — Install the Chromium browser for Playwright

```powershell
playwright install chromium
```
Playwright's Python package does **not** ship a browser binary — this
downloads Chromium separately (a few hundred MB). Expected output ends with
something like `Chromium ... downloaded to ...`. This step is required even
though `playwright` is already `pip install`ed; skipping it causes browser
launch failures (see Troubleshooting).

### STEP 9 — Run the Flask application

```powershell
python app.py
```
Expected output:
```
 * Serving Flask app 'app'
 * Debug mode: off
WARNING: This is a development server. Do not use it in a production deployment.
 * Running on http://127.0.0.1:5000
Press CTRL+C to quit
```
**Keep this terminal window open** — it is both the web server and, as
explained below, the control for stopping a recording.

### STEP 10 — Open the application in a browser

Go to:
```
http://127.0.0.1:5000
```
You should see the **AutoFlow QA** dashboard: a URL input, three buttons
(Launch Browser / Connect Database / System Status), a "Recorded Tests"
panel, and a "Raw Result" panel.

---

## Running the App

The Flask entry point is `app.py`, and it is run directly:

```powershell
python app.py
```

The exact server configuration, taken directly from the bottom of `app.py`:

```python
if __name__ == "__main__":
    app.run(
        host="127.0.0.1",
        port=5000,
        debug=False,
        threaded=True,
    )
```

- **Host/port**: `127.0.0.1:5000` — not exposed outside your machine.
- **`debug=False`**: no auto-reload, no interactive debugger. If you edit
  Python source, you must stop (`Ctrl+C`) and re-run `python app.py`.
- **`threaded=True`**: Flask can handle more than one request at a time.
  This matters because recording a browser session can take an arbitrarily
  long time (it waits for you to press Enter) — with threading on, the
  `/status` and `/api/recordings` endpoints stay responsive while a
  recording is in progress, since the actual recording work runs on its
  own background thread rather than Flask's request thread.

---

## Recording Flow

Recording is tied to the **Launch Browser** button; stopping it can be done
either from the dashboard's **Stop Recording** button or, as before, by
pressing **ENTER** in the terminal running `app.py` — both trigger the exact
same stop mechanism (there is no second/duplicate implementation). This is
the actual mechanism implemented in `app.py` / `recorder/record_session.py`
— here is exactly what happens, step by step:

1. You type a URL into the dashboard's URL field and click **Launch
   Browser**.
2. The frontend sends `POST /api/browser/launch` with `{"url": "..."}`.
3. Flask spawns a dedicated background thread for this session (Playwright's
   sync API must stay on the thread that created it, and the thread may
   block for a long time waiting on your terminal input — it can't run on
   Flask's own request thread).
4. On that thread, Playwright launches a **visible (headed)** Chromium
   window (`headless=False`). If a headed launch fails (e.g. no display
   available), it automatically falls back to headless.
5. The browser navigates to your URL and waits for it to load
   (`domcontentloaded`, then up to 8s for `networkidle`, non-fatal if that
   times out).
6. `Recorder.start()` runs immediately: it injects `action_capture.js` into
   the page and exposes a `recordAction` binding so the page can call back
   into Python.
7. Playwright's own `/api/browser/launch` response tells the dashboard the
   page loaded — the "Browser Launch Result" panel updates with the visited
   URL and page title, a **Stop Recording** button appears, and a status
   badge (polled from `GET /api/recording/status`) tracks the session
   through `launching` → `recording` → `stopping` → `completed`/`failed`.
8. **You perform actions in the visible browser window** — click, type,
   scroll, submit, navigate, open new tabs. Every meaningful action is
   captured (see [Supported Action Types](#supported-action-types)) and
   printed live to the **terminal** running `app.py`, e.g.:
   ```
   [RECORDED] CLICK
   Element: Search Amazon
   Locator: #twotabsearchtextbox
   ```
9. **To stop recording**, either click the dashboard's **Stop Recording**
   button (`POST /api/recording/stop`) or click into the terminal window
   running `python app.py` and press **ENTER** — both set the exact same
   internal stop signal (`recorder/record_session.py`'s `Recorder.stop()`
   is the one true stop path either way is routed through). Clicking Stop
   Recording again while a stop is already in progress, or with nothing
   active, is a safe no-op rather than an error. (If the browser is closed
   unexpectedly instead, or a navigation gets permanently stuck, the
   recorder also detects that and stops on its own, logging why.)
10. On stop, the recorder sorts all captured actions by their true
    timestamp (some actions can arrive at Python slightly out of order due
    to double-click disambiguation — sorting by timestamp restores the real
    order), and the JSON is saved via `storage/repository.py`.
11. Immediately after saving, `generator/script_generator.py` is called
    automatically to turn that same JSON into a standalone Python script
    under `generated_scripts/`. Both paths are printed to the terminal.

---

## Real Recording Example

Using a simple, safe demo site:

**Open:**
```
https://demoqa.com
```

**Perform (in the launched browser window):**
1. Click **Elements**
2. Click **Text Box**
3. Click the **Full Name** field, type a name
4. Click the **Email** field, type an email
5. Click **Submit**

**What you'll see printed live in the terminal**, in the order you did it:
```
[RECORDED] CLICK
Element: Elements
Locator: ...

[RECORDED] CLICK
Element: Text Box
Locator: ...

[RECORDED] CLICK
Element: (Full Name input)
Locator: #userName

[RECORDED] FILL
Element: (Full Name input)
Locator: #userName
Value: Jane Doe

[RECORDED] CLICK
Element: (Email input)
Locator: #userEmail

[RECORDED] FILL
Element: (Email input)
Locator: #userEmail
Value: jane@example.com

[RECORDED] CLICK
Element: Submit
Locator: #submit
```

**Then, in that same terminal, press ENTER.** You'll see:
```
==================================================
RECORDING STOPPED

Total actions: 7
Stop reason: terminal_enter

JSON saved:
D:\new_test\storage\recordings\session_20260813_160512.json

Python script generated:
D:\new_test\generated_scripts\session_20260813_160512_script.py
==================================================
```

Refresh the dashboard (or click **Refresh** in the Recorded Tests panel) and
this new recording appears as a card.

---

## Where Recordings Are Saved

From `storage/repository.py`:

```python
BASE_DIR = Path(__file__).resolve().parent.parent
RECORDINGS_DIR = BASE_DIR / "storage" / "recordings"
```

So, relative to the project root:
```
storage/recordings/
```

Recordings are saved as JSON, named `session_<YYYYMMDD_HHMMSS>.json`, e.g.:
```
storage/recordings/session_20260812_131205.json
```

Two subfolders hold derived recordings, never the originals they came from:
`storage/recordings/edited/<name>_edited.json` (from Save Edited JSON) and
`storage/recordings/trimmed/<name>_trimmed.json` (from the Trim screen) —
see [Dashboard: Viewing and Editing a Recording](#dashboard-viewing-and-editing-a-recording).
All three locations show up identically in the Dashboard's recording list.

**Actual top-level fields** (verified against a real saved file — nothing
here is invented):

| Field | Meaning |
|---|---|
| `name` | Filename stem, e.g. `session_20260812_131205` |
| `session_id` | Random hex id generated per recording session |
| `start_url` | The URL Launch Browser opened |
| `recorded_at` | ISO timestamp when `Recorder.stop()` ran |
| `saved_at` | ISO timestamp when the file was written to disk |
| `stop_reason` | `terminal_enter`, `browser_closed`, `navigation_error`, or `application_error` |
| `total_actions` | Number of actions in the list below |
| `actions` | Ordered list of captured actions |

**Each action's actual fields:**

| Field | Meaning |
|---|---|
| `action_type` | One of the types listed in [Supported Action Types](#supported-action-types) - `click`/`dblclick`/`right_click`/`fill`/`select`/`submit`/`press`/`navigate`/`scroll` from live recording, or any of the validation/count/capture types added via the Recording Editor |
| `value` | Typed text / pressed key / selected option (or `null`) |
| `locator_profile` | id, css_path, xpath, text, tag, attributes — or `null` for navigate/scroll |
| `bounding_box` | `{x, y, width, height}` at capture time — or `null` for navigate/scroll |
| `page_url` | The page the action happened on |
| `timestamp` | ISO-8601 UTC timestamp with milliseconds |

---

## Supported Action Types

Directly from `recorder/action_capture.js`, these are the action types
actually produced by **recording live browser interaction**:

| Action type | How it's captured |
|---|---|
| `click` | Held briefly (300ms) to distinguish from a double-click; if no second click on the same element follows, it's sent as a single click. |
| `dblclick` | Real browser `dblclick` event on the same target within that 300ms window. |
| `right_click` | Browser `contextmenu` event (the only event fired for the secondary mouse button). |
| `fill` | Committed on `change` (blur), **and** flushed synchronously on Enter/Tab keydown so a search box's value isn't lost when Enter immediately submits/navigates before blur fires. Deduped so the same committed value is never sent twice. |
| `select` | `change` event on a `<select>` element. |
| `submit` | Native form `submit` event — usually **suppressed** if it's redundant with a click/press already recorded for the same action (see next section), so it rarely appears as its own step in practice. |
| `press` | `keydown` for `Enter`, `Tab`, `Escape`, or `Backspace` only (Backspace while editing text is ignored — the eventual `fill` already captures the corrected value; recording every keystroke would be noise). |
| `navigate` | Detected on the **Python** side via Playwright's `framenavigated` event, not in JS (a page can't reliably report its own navigation while it's unloading). Debounced — see below. |
| `scroll` | **Listens for the real DOM `scroll` event**, not wheel ticks — this deliberately replaced an earlier wheel-based approach that could miss scrolling on pages whose own JS intercepts the wheel event to drive custom scroll behavior (confirmed via a real repro where visible scrolling produced zero recorded actions under the old approach). Works for the window/page itself *and* any nested `overflow:auto`/`scroll` container, whatever actually triggered it (mouse wheel, scrollbar drag, keyboard Page Down/arrows/Space, touch, or a script's own `scrollTo()`). A burst of scroll events for one continuous gesture is collapsed into a single action, committed 250ms after the last event in that burst ("settle on pause"), capturing the position from *before* the burst started to *after* it settled — not per-event. |

Recordings can also contain many more action types — `check`,
`validate`/`validate_element`/`validate_text`/`validate_attribute`/
`validate_visible`/`validate_value`/`validate_enabled`, `check_checked`,
`capture_value`/`compare_value`, `count_elements`/`compare_counts`/
`count_summary`, `capture_list`/`compare_list_overlap`,
`detect_duplicates`, `validate_value_range`, `click_if_exists`,
`screenshot`, `tab_open`/`tab_switch`/`tab_close` — but these are not
captured from live browser interaction; they're added afterward through
the Recording Editor's **Add Action** dialog (see
[Dashboard: Viewing and Editing a Recording](#dashboard-viewing-and-editing-a-recording)),
each with its own guided fields and (for the ones that need one) an XPath
+ Pick Element locator. `generator/script_generator.py` has a real handler
for every one of these — they're not just UI stubs.

**Duplicate suppression that's actually implemented:**
- A `submit` event within 0.6s of the click that caused it is dropped (the
  click already represents that step).
- Pressing Enter in a form field makes the browser fire its own synthetic
  `click` on the implicit submit button and a `submit` event a moment
  later — both are suppressed for up to 700ms after the Enter keydown,
  since they're the same action `press Enter` already recorded.
- Real navigations are often a **chain** of redirects (tracking URLs,
  interstitials). The recorder waits up to 4.5 seconds after the last hop
  before committing a single `navigate` action, instead of recording every
  intermediate URL. This is a best-effort heuristic, not a guarantee — an
  unusually slow redirect chain can still occasionally produce two
  `navigate` entries.
- A navigation within 1.5 seconds of a click/submit that already got
  recorded is treated as caused by that click and isn't recorded again.

---

## Locator / Selector System

Every captured element gets a full **locator profile**, not just one
selector — captured in `action_capture.js`:

```
id, css_path, xpath, text, tag, attributes{data-testid, data-test, data-cy,
name, aria-label, placeholder, role, title, href, type}
```

At **replay time**, `generator/script_generator.py`'s `resolve_and_act()`
(used by `click`/`dblclick`/`right_click`/`fill`/`select`/`submit`/`press`/
`check`) tries these, in this exact order, stopping at the first one that
finds an element:

```
 1. data-testid
 2. data-test
 3. data-cy
 4. id
 5. name
 6. aria-label
 7. placeholder
 8. title
 9. role              (Playwright get_by_role with accessible name)
10. href               (for links)
11. text + tag         (visible text combined with tag name)
12. position fallback  (same structural position among similar siblings, when content can't be matched at all)
13. css_path           (id/nth-of-type chain captured at record time)
14. xpath
15. bounding box       (last resort, click-type actions only: click the recorded x/y coordinates)
```

The newer element-level validation actions (`validate_text`,
`validate_attribute`, `validate_visible`, `validate_value`,
`validate_enabled`, `capture_value`, `count_elements`, and others — see
[Supported Action Types](#supported-action-types)) go through a related but
simpler resolver, `_resolve_element()`, with the same priority order minus
`position fallback` and `bounding box` (a validation reads the page rather
than acting on it, so a coordinate/positional guess isn't a meaningful
substitute for a real match).

**Why store all of them:** a page can change between when you recorded and
when you replay — an `id` that got auto-generated differently, a CSS class
that changed. Trying several independent signals in priority order (most
stable/intentional first, most fragile last) makes replay much more likely
to still find the right element even after minor page changes.

**What happens if none of the normal strategies match:** for click-type
actions only (`click`, `dblclick`, `right_click`), the bounding-box
coordinates captured at record time are used as a last resort — literally
clicking at that pixel position on the page. Non-click actions (`fill`,
`select`, `submit`, `press`) have no coordinate fallback: they need a real
element to act on, so they're marked failed if nothing resolves.

**Locator resolution reporting:** every step's replay result carries a
`locator_report` — a plain-English translation of which strategy actually
matched (e.g. *"More information... found using CSS path. (resolved in
16ms)"*, or *"... could not be resolved using any stored locator."* if
nothing did), plus a numeric fallback level and a `weak` flag for the two
loosest, purely structural/positional tiers. Raw selector strings are kept
out of the main dashboard/report view by default, available behind an
"Advanced"/"Advanced locator details" disclosure. The Recording Editor
additionally shows this as a 🟢🟡🟠🔴 health badge per step, sourced from
that recording's own most recent Replay result (see
[Dashboard: Viewing and Editing a Recording](#dashboard-viewing-and-editing-a-recording)).

**Fragile flag:** a step is flagged `fragile` (shown as amber in the HTML
report) if it only resolved via `text+tag` or `bounding_box` — these are
exactly the two strategies most likely to break the next time the page's
content or layout changes even slightly.

**Locators here are not claimed to be 100% reliable.** This is an
intentionally layered best-effort system, not a guarantee — dynamic pages,
A/B tests, and DOM structure changes can still break a replay step even
with every fallback strategy available to it.

---

## Dashboard: Viewing and Editing a Recording

This is a real, working feature of the current codebase — a recording does
not have to be replayed exactly as captured. From the dashboard's "Recorded
Tests" panel, every saved recording shows as a card with **Name**, **action
count**, **saved path**, **saved time**, and **View / Edit**, **Trim**,
**Replay**, and **View Last Log** buttons.

Clicking **View / Edit** opens `GET /recording/edit?path=...`, which loads
`templates/recording_editor.html`. That page calls `GET
/api/recordings/view?path=...` to fetch the recording's full JSON (this is
a pure read — opening a recording never modifies the original file) and
renders:

- **Metadata**: Name, Total Actions, Start URL, Recorded At, Saved At, Stop
  Reason.
- **Every action, in order**, each as its own row showing its type and a
  🟢🟡🟠🔴 **locator health badge** when this recording has been replayed at
  least once (pulled from that last Replay's own result via `GET
  /api/recordings/last_result` — 🟢 stable/attribute-based match, 🟡 a
  fallback text/structural match was used, 🟠 a weak position/coordinate
  fallback was used, 🔴 unresolved last time). Expanding a row shows a
  plain-English "Locator strategy / Resolution / Recommendation" summary,
  with the raw `css_path`/`xpath` tucked behind an "Advanced locator
  details" disclosure rather than shown by default.
  - **Up** / **Down** buttons — reorder this action (disabled at the
    top/bottom of the list)
  - **Delete** button — removes this action
  - **Add Action Before/After** buttons on every row

**Add Action** opens a guided dialog: pick an action type from a dropdown
(every type in [Supported Action Types](#supported-action-types)), and the
dialog renders exactly the fields that type needs (e.g. Fill shows a Value
field; Count Elements shows "store count as" + an optional expected count).
For any type that needs a locator, the dialog shows an XPath field plus a
**Validate** button (checks it against the real page state a Replay would
reach at that exact insertion point, via `POST
/api/recordings/validate_locator` — never touches the saved recording) and
a **🎯 Pick Element** button, which opens a real, visible browser window
(reusing the exact same locator-generation logic recording itself uses),
lets you hover to highlight and click the element you mean, and fills the
XPath field in automatically.

**None of this touches the saved file on disk until you click.** All
edits/deletes/adds/reorders/Add Action changes happen only in the browser
tab's in-memory state.

**Save Edited JSON** sends the current in-memory state to `POST
/api/recordings/save`, which writes it into `storage/recordings/edited/` —
the original recording is never overwritten. Unlike an earlier version of
this feature, the edited filename is **stable, not timestamped**:
```
storage/recordings/edited/<original_name>_edited.json
```
e.g. `storage/recordings/edited/session_20260812_121227_edited.json` — every
subsequent **Save Edited JSON** click for the same original recording
overwrites that same file (and its generated script) with the latest edit,
rather than piling up a new dated copy each time. It still shows up in the
Dashboard exactly like any other recording, including its own **View /
Edit** button, and the editor additionally shows the untouched original
side-by-side for comparison when you reopen an edited recording.

There is also a separate **Trim** screen (`GET /recording/trim?path=...`) —
a checklist of one recording's steps where you pick a subset to keep,
saved as a brand-new `storage/recordings/trimmed/<name>_trimmed.json`
recording; the source recording is never modified.

**Fill → Navigation editing:** if you edit a `fill`/`select` step's value
(e.g. changing a search term) and a later recorded `navigate` step's URL
was originally derived from that same input (a search-results URL baked in
at record time), replay follows the app's own real, edited-input-driven
navigation instead of forcing the stale pre-edit URL — this used to
silently force the old URL; it's fixed now (flagged with a visible warning
in the step's report either way, so which happened is never silent). An
`navigate` step genuinely unrelated to any preceding fill/select (an
explicit link, a fixed "next page" URL, ...) is unaffected and still
replays exactly as recorded.

---

## Generated Script

```
Recording JSON (storage/recordings/*.json)
        │
        ▼
generator/script_generator.py  ->  generate_script()
        │
        ▼
generated_scripts/<name>_script.py
```

Filename pattern: `<recording name>_script.py`, e.g.:
```
generated_scripts/session_20260812_131205_script.py
```

This is a **standalone Playwright script** — it does not import anything
else from this project. You can open it and read exactly what it will do
(the `resolve_and_act` locator-priority logic is fully inlined), or copy it
elsewhere and run it on its own as long as `playwright` is installed.

**Running it directly:**
```powershell
python generated_scripts\session_20260812_131205_script.py [qa_url] [output_json_path] [screenshot_dir] [headless] [product_name]
```

All five arguments are optional, taken exactly from the script's own
`__main__` block:

| Position | Argument | Default if omitted |
|---|---|---|
| 1 | `qa_url` | The originally recorded URL |
| 2 | `output_json_path` | `report.json` inside the same auto-generated `screenshot_dir` below (never "nowhere") |
| 3 | `screenshot_dir` | `generated_scripts/screenshoots/<slugified-recording-name>_<timestamp>/` |
| 4 | `headless` | `"0"` — i.e. **headed** (visible) when run by hand |
| 5 | `product_name` | Not set — product validation is skipped entirely |

Running it with no arguments at all replays against the originally recorded
URL in a visible browser window, which is handy for watching a replay live.
**Note: when the dashboard triggers a replay** (via `/api/test/run` or
`/api/test/run/start`, see next section), `executor/run_execution.py`
always passes `headless="0"` (headed/visible) too, deliberately — a
dashboard-triggered Replay opens a real, visible browser window so you can
watch it run, the same as running the generated script by hand.

---

## QA Replay Flow

```
Recording (existing or edited JSON)
        │
        ▼
generator/script_generator.py  ->  generate_script()
        │
        ▼
generated_scripts/<name>_script.py
        │
        ▼  (run as a subprocess by executor/run_execution.py)
Chromium replays every action against qa_url, headed (visible)
        │
        ├── screenshots grouped by stage + report.json written incrementally
        ▼
generated_scripts/screenshoots/<run_id>/report.json
        │
        ▼  (read back and interpreted by run_execution.py once the run ends)
+ UI-element / content / screenshot-diff / product validation
        │
        └── validation/report_generator.py -> generated_scripts/screenshoots/<run_id>/report.html
```

**This now has a dashboard UI, not just an API.** Every recording card in
the Dashboard's "Recorded Tests" panel has a **Replay** button, which drives
this same pipeline through two endpoints instead of one blocking call —
`POST /api/test/run/start` kicks off the replay and returns immediately with
a `run_id`, then the dashboard polls `GET /api/test/run/progress?run_id=...`
to render live step-by-step progress (current step, pass/fail/warning
counts, elapsed time) until the run finishes, at which point that same
endpoint returns the full result. The original single blocking call,
`POST /api/test/run`, still exists unchanged underneath and is what a
script/curl call should use directly:

```powershell
curl -X POST http://127.0.0.1:5000/api/test/run ^
  -H "Content-Type: application/json" ^
  -d "{\"qa_url\": \"https://your-qa-site.com\", \"recording_path\": \"storage/recordings/session_20260812_131205.json\"}"
```

**Request fields**, read directly from `app.py` (shared by both
`/api/test/run` and `/api/test/run/start`):

| Field | Required | Purpose |
|---|---|---|
| `qa_url` | Yes | The target site to replay against |
| `recording_path` | No | Which saved recording to replay; if omitted, an empty/no-op test case is used |
| `expected_content` | No | Text that must appear on the final page for the run to pass |
| `expected_screenshot` | No | Path to a baseline PNG to diff the final screenshot against |
| `product_to_verify` | No | A product name to look for on whatever page replay ends on |
| `screenshot_threshold` | No | Overrides the default screenshot-diff tolerance (see [Screenshot Comparison](#screenshot-comparison)) |
| `screenshot_ignored_regions` | No | A list of `{x, y, width, height}` rectangles to mask out of the screenshot diff |
| `screenshot_strict` | No | `true` disables the default anti-aliasing noise tolerance for an exact pixel-for-pixel diff |

Response fields (both endpoints, once done): `status` (`PASS`/`FAIL`),
`message`, `steps`, `html_report` (path), `json_report` (path).
`/api/test/run/start` additionally returns `run_id` immediately; poll
`/api/test/run/progress?run_id=...` for `done`, `steps`, `total_steps`,
`passed`/`failed`/`warnings` counts until `done` is `true`.

---

## QA URL Mapping

From `generator/script_generator.py`'s `to_qa_url()`, embedded in every
generated script:

- If a recorded `navigate` action's URL has **no domain** (a relative
  path), it's pointed at whatever host you're replaying against.
- If a recorded URL's domain **matches** the domain you originally recorded
  against (`PROD_URL`, the recording's `start_url`), its scheme and host
  are swapped for the QA host, and the **path and query string are kept
  exactly as recorded**.
- If a recorded URL's domain is **different** from what you recorded
  against (a third-party link), it's left completely alone — no guessing.

**Example:**

Recorded against:
```
https://production.example.com/
```
A recorded `navigate` step captured:
```
https://production.example.com/products?id=10
```
Replaying with `qa_url = https://qa.example.com`, that step becomes:
```
https://qa.example.com/products?id=10
```
The path (`/products`) and query (`?id=10`) are preserved; only the
scheme+host are swapped.

---

## Screenshot Storage

**Note: this section previously described `screenshots/execution_runs/` —
that path no longer exists in the code.** The current output location, from
`executor/run_execution.py`'s `execute_test()`/`start_replay()`:

```python
run_dir = BASE_DIR / "generated_scripts" / "screenshoots" / run_id
```

(`screenshoots` — that's the actual directory name in the code, not a typo
in this README.) Each replay (`/api/test/run` or `/api/test/run/start`)
creates one folder, named `<recording-name-slug>_<YYYYMMDD_HHMMSS>`:
```
generated_scripts/screenshoots/<run_id>/
```
Real example:
```
generated_scripts/screenshoots/session_20260917_142337_20260919_120352/
```

Inside that folder:

| File | Contents |
|---|---|
| `<stage-name>/img1.png`, `img2.png`, ... | Screenshots taken during replay, grouped into per-stage subfolders (one stage per distinct page/route visited — see the Screenshot Stages viewer, `/run/stages?run_dir=...`) and numbered sequentially within the whole run, not per-stage |
| `report.json` | The full result (see below) — written incrementally, once per completed step, during the run itself (so a dashboard polling `/api/test/run/progress` can show live step-by-step progress), then finalized with UI-element/content/screenshot/product validation once the run ends |
| `report.html` | The self-contained HTML report (see [HTML Report](#html-report)) |

Separately, the top-level `screenshots/<timestamp>/img1.png` folder holds
one best-effort screenshot taken right when **Launch Browser** first opens a
page for recording — a different, unrelated purpose from the replay output
above.

---

## Execution JSON

**Note: this section previously described `storage/executions/
execution_<id>.json` — nothing in the current code writes to that
directory anymore** (`storage/repository.py` still defines
`save_execution()`, but no caller in `app.py` or `executor/` invokes it; any
files already in `storage/executions/` are historical leftovers from an
earlier version of the project, the same situation as `storage/searches/`
below). The current, actually-written result file is `report.json` inside
each run's own `generated_scripts/screenshoots/<run_id>/` folder described
above.

**Actual top-level fields** (verified against a real saved file):

| Field | Meaning |
|---|---|
| `status` | `PASS` or `FAIL` (overall — see below for what counts) |
| `message` | Human-readable summary, e.g. `"all steps resolved and validations passed"` or `"steps failed: [5]; UI elements missing at steps: [5]"` |
| `diagnostic` | Raw technical detail (a Playwright error string) for a run that failed before any step ran at all - kept separate from `message` so the dashboard's user-facing summary never shows a raw stack trace |
| `qa_url` | The URL that was actually replayed against |
| `steps` | Every replayed action: `index`, `action_type`, `strategy_used`, `element_found`, `success`, `error`, `warning`, `effect_verified`, `screenshot`, `fragile`, `duration`, `locator_report` (see [Locator / Selector System](#locator--selector-system)), `expected`/`actual` (populated for validation-style steps) |
| `ui_elements` | One entry per non-navigate/scroll step: `index`, `action_type`, `element_found`, `locator_used`, `status`, `message` |
| `ui_elements_status` | `PASS` if every UI element resolved, else `FAIL` |
| `content_check` | `true`/`false` if `expected_content` was requested, else `null` |
| `screenshot_diff` | `{match, diff_ratio, note}` if `expected_screenshot` was requested, else `null` |
| `product_validation` | Full product-search result if `product_to_verify` was requested, else `null` |
| `final_screenshot` | Path to the full-page final screenshot |
| `run_id` | The same id used for the run's screenshot folder name |

**Overall `status` is `PASS` only if all of these hold:** every step
succeeded, every UI element resolved, content check didn't explicitly fail,
screenshot diff didn't explicitly mismatch, the product was found (if
requested), and the run didn't fail before any step even started (e.g. an
unreachable `qa_url` — that specific case used to be silently misreported
as `PASS` when there were zero recorded actions to fail; it's correctly
`FAIL` now).

---

## HTML Report

```
Execution result (the dict above)
        │
        ▼
validation/report_generator.py  ->  generate_report()
        │
        ▼
generated_scripts/screenshoots/<run_id>/report.html
```
Real example:
```
generated_scripts/screenshoots/session_20260812_130826_20260919_120352/report.html
```
(This replaces the report location an earlier version of this README
described, `reports/report_<run_id>.html` — that `reports/` folder is now
legacy/unused, see [Current Limitations](#current-limitations).)

Every screenshot referenced by the result is **embedded directly into the
HTML as a base64 `data:image/png;base64,...` URI** — the report is a single
file with no external dependencies; you can email it or open it from
anywhere without also handing over the `screenshots/` folder.

**Sections actually present in `templates/report.html`** (verified — this
is the complete list, in order):

1. **Overall banner** — PASS/FAIL + the message
2. **Step Validations** *(new)* — a stats line ("N steps executed · N/M
   actions passed · N/M validations passed · N failed · N locator
   warnings") plus one pass/fail card per validation-style step
   (`validate_*`, `check_checked`, `compare_*`, ...), each showing
   Expected/Actual/Step/Element when it failed
3. **Validations** — Expected Content Found (pill), Screenshot Diff (pill
   with ratio, or "not requested"/"skipped")
4. **Product Validation** — only rendered if a product was requested:
   PASS/FAIL banner, Requested Product, Found (Yes/No), Match Type (EXACT
   MATCH / POSSIBLE-SIMILAR MATCH / -), Position + Product Title + Product
   URL if found, or Reason + Results Checked if not, plus an embedded
   evidence screenshot
5. **Execution** — Total Steps, Passed, Failed, First Failed Step
6. **Steps** — a table: index, action, locator strategy (friendly label,
   with a "weak" pill when applicable and the raw strategy string behind
   an "Advanced" disclosure), PASS/FAIL, amber "fragile" tag if applicable,
   error text
7. **UI Elements** — a table of which elements were found/not found
8. **Screenshots** — every step screenshot plus the final full-page
   screenshot

---

## Screenshot Comparison

From `validation/compare.py`:

```python
DEFAULT_THRESHOLD = 0.02          # fraction of max possible pixel difference
DEFAULT_PIXEL_NOISE_FLOOR = 8     # per-channel delta (0-255) treated as noise
```

- Resizes the actual screenshot to match the baseline's dimensions if they
  differ, then computes the sum of per-pixel RGB differences as a fraction
  of the maximum possible difference, using `ImageStat.Stat(diff).sum` for
  the per-band sums.
- **By default**, a per-channel difference of 8 or less is treated as 0
  before summing — small enough to absorb ordinary anti-aliasing/font-
  rendering noise between two otherwise-identical renders, nowhere near
  enough to hide a real visual change. Pass `strict: true` (via the API's
  `screenshot_strict` field) for the exact-tolerance original behavior
  (every nonzero pixel delta counts).
- `match: true` if `diff_ratio <= threshold` (default `0.02`, overridable
  per-call via `screenshot_threshold`), else `false`.
- **`ignored_regions`** (API field: `screenshot_ignored_regions`) — an
  optional list of `{x, y, width, height}` rectangles (in the baseline
  image's own pixel coordinates), blacked out identically on both images
  before diffing. Always opt-in (empty by default — nothing is masked
  unless you name a region); intended for a timestamp, an ad slot, a
  "Welcome, &lt;name&gt;" banner, or anything else expected to legitimately
  differ every run.
- **If the baseline screenshot doesn't exist on disk:** the comparison is
  **skipped**, not failed — `{match: null, diff_ratio: null, note: "baseline
  screenshot not found at ..., skipped"}`. This does not fail the overall
  run.
- **If no actual screenshot was captured from the run:** similarly skipped
  with a `note` explaining why, not treated as a hard failure.
- This is a deterministic pixel-sum diff, not a perceptual/structural
  comparison and not an AI/vision service — good enough to catch a badly
  broken layout or a real visual regression, not a fine-grained perceptual
  diff tool.

---

## Database Status

```
GET /api/database/connect
```
Always returns, verbatim from `app.py`:
```json
{"success": false, "configured": false, "message": "Database integration is not configured yet."}
```
**Database integration is not implemented in the current project.** This
endpoint exists only as a placeholder the "Connect Database" dashboard
button calls — clicking it will always show this message.

---

## Retention / Cleanup

From `storage/retention.py`:

```python
RETENTION_DAYS = 30
```

An age-only sweep over the directories this project accumulates files in:
`storage/recordings/` (+ `edited/`, `trimmed/`), `generated_scripts/`
(+ `edited/`, `fill_diagnostics/`), `generated_scripts/screenshoots/` (every
past run's screenshots + report), `screenshots/` (launch screenshots), and
`reports/`. Nothing runs automatically — **this project has no background
scheduler/cron** — a sweep only happens when `GET`/`POST
/api/maintenance/cleanup` is actually called.

- **`GET`** (or a query string) is always a **preview** — it reports what
  would be archived/deleted without touching anything, regardless of any
  `dry_run` value passed.
- **`POST`** with `{"dry_run": false}` performs it for real. Optional body
  fields: `retention_days` (default `30`), `mode` (`"archive"`, the
  default — moves matched items under `retention_archive/<label>/`,
  recoverable — or `"delete"`, which removes them for good).
- **Safety, all enforced in `storage/retention.py` itself:** a recording is
  never touched while a recording session is actively in progress; a run
  folder is never touched while its replay is still in-flight, regardless
  of age; every candidate path is verified to actually resolve inside one
  of the configured directories before anything happens to it; a
  file that's already gone by the time it's processed is logged and
  skipped, never an error that aborts the rest of the sweep.

---

## API Reference

Every route below is taken directly from `app.py` — nothing here is
invented, and nothing implemented in `app.py` is omitted.

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/` | Renders the Dashboard (`index.html`) |
| GET | `/api/recordings` | Lists all saved recordings for the Dashboard panel |
| GET | `/recording/edit?path=...` | Renders the Recording Editor page for one recording |
| GET | `/api/recordings/view?path=...` | Returns one recording's full JSON (used by the editor page) |
| GET | `/api/recordings/last_result?path=...` | Returns the most recent Replay result for one recording, if any (used by "View Last Log") |
| POST | `/api/recordings/validate_locator` | Live-checks a typed XPath against the real page state a Replay would reach at that insertion point (used by the Add Action dialog) |
| POST | `/api/recordings/pick_element/start` | Starts a Pick Element session - opens a real browser at the right page state and waits for a click |
| GET | `/api/recordings/pick_element/status?pick_id=...` | Polled while a Pick Element session is live |
| POST | `/api/recordings/save` | Saves the edited recording as a new `*_edited.json` file (one stable name per original - re-saving overwrites it, not a new timestamped copy each time) |
| GET | `/recording/trim` / `GET /api/recordings/trim_view` / `POST /api/recordings/trim_save` | Trim screen: view a recording's steps as a checklist, save a hand-picked subset as a new `*_trimmed.json` recording |
| POST | `/api/browser/launch` | Launches a browser, navigates, and starts recording (body: `{"url": "..."}`) |
| POST | `/api/recording/stop` | Stops the active recording session (same effect as pressing ENTER in the terminal) - idempotent, safe to call with nothing active |
| GET | `/api/recording/status` | Polled by the dashboard while recording: `phase` (`idle`/`launching`/`recording`/`stopping`/`completed`/`failed`), plus the finished recording's path/name/action count once done |
| GET | `/api/database/connect` | Always returns "not configured" — placeholder only |
| GET | `/status` | Current session state: `flask`, `playwright_installed`, `browser_active`, `recording`, `current_url` |
| POST | `/api/test/run` | Generates + replays a script against a QA URL and produces a report - blocks until finished |
| POST | `/api/test/run/start` | Same replay, but returns immediately with a `run_id` for live-progress polling (used by the Dashboard's Replay button) |
| GET | `/api/test/run/progress?run_id=...` | Polled for live step-by-step progress; returns the full result once the run is done |
| GET | `/run/stages?run_dir=...` / `GET /api/runs/stages` / `GET /screenshots/raw?path=...` | Screenshot Stages viewer for one run - browses that run's screenshots grouped by page/stage |
| GET | `/screenshots` / `GET /api/screenshots/sessions` / `GET /api/screenshots/stages` / `GET /api/screenshots/images` | Dashboard-level Screenshots viewer listing every past run |
| GET/POST | `/api/maintenance/cleanup` | Retention sweep over old recordings/scripts/run folders/reports (see [Retention / Cleanup](#retention--cleanup)) - GET always previews only, POST needs `{"dry_run": false}` to actually archive/delete anything |

---

## Full End-to-End Example

Only steps actually supported by the current code/UI/API are listed.

**Recording (via the Dashboard UI):**
1. Enter a production-like URL, click **Launch Browser**.
2. Perform your actions in the opened window (click, fill, submit,
   navigate, scroll — whatever the real flow is).
3. Click **Stop Recording** in the dashboard, or press **ENTER** in the
   `app.py` terminal.
4. JSON is saved to `storage/recordings/`, and a script is generated to
   `generated_scripts/` automatically.

**Optional — editing before replay (via the Dashboard UI):**
5. Refresh the dashboard, click **View / Edit** on the new card.
6. Modify field values, delete unwanted steps, add new steps via the guided
   **Add Action** dialog (optionally using **🎯 Pick Element** to fill in a
   locator by clicking the real element), reorder with Up/Down.
7. Click **Save Edited JSON** — `storage/recordings/edited/<name>_edited.json`
   is created (or overwritten, if you'd already saved an edit of this
   recording before) and shows up in the Dashboard list.

**Replaying against QA (via the Dashboard's Replay button, or the API):**
8. Click **Replay** on the recording's card - the dashboard calls
   `POST /api/test/run/start`, then polls `GET /api/test/run/progress` for
   live step-by-step progress until the run finishes. (Equivalently, call
   `POST /api/test/run` directly with `qa_url` set to your QA/staging URL
   and `recording_path` pointing at either the original or the edited
   JSON - it blocks until done and returns the same final result.)
9. The existing generator turns that JSON into a script (again, or reuses
   the one from step 4/7 if you generated it yourself).
10. The existing executor runs that script as a subprocess against
    `qa_url`, headed (visible), capturing screenshots grouped by
    page/stage plus a final screenshot.
11. `generated_scripts/screenshoots/<run_id>/report.json` is written
    (incrementally, step by step, then finalized).
12. `generated_scripts/screenshoots/<run_id>/report.html` is generated
    with everything embedded, including validation cards for any
    validate_*/check_checked/compare_*/... steps in the recording.
13. Open that HTML file in any browser — no server required, no
    external screenshot files needed.

---

## Exact File Path Table

| Purpose | Exact Path |
|---|---|
| Application entry point | `app.py` |
| Dependencies | `requirements.txt` |
| Shared helpers | `utils.py` |
| Recorder (Python side) | `recorder/record_session.py` |
| Recorder (injected JS) | `recorder/action_capture.js` |
| Pick Element | `recorder/pick_element.py` |
| Script generator | `generator/script_generator.py` |
| Executor | `executor/run_execution.py` |
| Screenshot comparison | `validation/compare.py` |
| Report generator | `validation/report_generator.py` |
| Storage (single source of truth for disk I/O) | `storage/repository.py` |
| Retention / cleanup sweep | `storage/retention.py` |
| Saved recordings | `storage/recordings/` (+ `edited/`, `trimmed/`) |
| Legacy/unused execution results | `storage/executions/` |
| Legacy/unused search results | `storage/searches/` |
| Generated Playwright scripts | `generated_scripts/` (+ `edited/`) |
| Per-run replay screenshots + `report.json`/`report.html` | `generated_scripts/screenshoots/<run_id>/` |
| Legacy/unused shared HTML reports | `reports/` |
| Launch screenshots (one per recording session start) | `screenshots/<timestamp>/` |
| Dashboard template | `templates/index.html` |
| Recording editor template | `templates/recording_editor.html` |
| Recording trim screen template | `templates/recording_trim.html` |
| Screenshot stages/viewer templates | `templates/run_stages.html`, `templates/screenshots_viewer.html` |
| Report template | `templates/report.html` |
| Dashboard JavaScript | `static/js/script.js` |
| Stylesheet | `static/css/style.css` |

---

## Troubleshooting

| Problem | Cause | Solution |
|---|---|---|
| `'python' is not recognized as an internal or external command` | Python isn't on PATH | Reinstall Python from python.org with "Add Python to PATH" checked, restart the terminal |
| `ModuleNotFoundError: No module named 'flask'` | `pip install -r requirements.txt` wasn't run, or the venv isn't activated | Run `venv\Scripts\activate` first (prompt should show `(venv)`), then `pip install -r requirements.txt` |
| `playwright._impl._errors.Error: Executable doesn't exist ...` | Chromium wasn't downloaded | Run `playwright install chromium` with the venv active |
| Browser launch fails / falls back to headless unexpectedly | No display available, or Chromium failed to start headed | Check the terminal log for the actual Playwright error; headless fallback is automatic and recording still works, just without a visible window |
| "Couldn't reach that URL - check it's correct and try again" | The URL is unreachable, DNS fails, or the site refuses the connection | Verify the URL loads in a normal browser; try with `https://` explicitly |
| Nothing prints when I click/type in the browser | The page hasn't finished the initial `Recorder.start()` injection, or you're interacting with a browser tab that isn't the one that was launched | Wait for "RECORDING STARTED" to print before acting; only the originally launched tab/page is recorded (new tabs are logged as a `navigate`, not followed) |
| Recording not saved / no JSON appears | You closed the terminal or killed the process before stopping cleanly | Click **Stop Recording** in the dashboard, or press ENTER in the `app.py` terminal, to stop cleanly; an unexpected browser close is still auto-saved, but killing the whole Python process is not |
| "A recording is already in progress" when clicking Launch Browser | A previous recording session is still active | Click **Stop Recording** (or press ENTER in the terminal) to end it first |
| Generated script fails immediately with a Python error | The recording JSON is malformed, or was hand-edited into invalid JSON via `/api/recordings/save` with something odd in the body | Re-open the file in the Recording Editor to check it loads without an error, or inspect the raw JSON in `storage/recordings/` |
| `/api/test/run` (or the dashboard's Replay button) returns `"the test script didn't complete - couldn't reach the QA URL or it crashed"` | The generated script's subprocess didn't produce a `report.json` — often a bad `qa_url`, or the script hit its timeout | Check `generated_scripts/screenshoots/<run_id>/` for partial output; try running the generated script directly (see [Generated Script](#generated-script)) to see the real Playwright error |
| Report not generated | `execute_test()`/`start_replay()` itself raised before `generate_report()` was reached, or the request never reached `/api/test/run` (e.g. wrong method/body) | Check the Flask terminal for a traceback; confirm the request is `POST` with a JSON body containing `qa_url` |
| Screenshot missing in report | The step's screenshot capture failed (page in a bad state) or the baseline path in `expected_screenshot` doesn't exist | The report shows "skipped" for a missing baseline rather than failing outright; check `generated_scripts/screenshoots/<run_id>/` directly for what was actually captured |
| Recording JSON missing after a run | The run crashed before `repository.save_recording()` was reached | Check the Flask/terminal logs for the actual exception; a save failure specifically now surfaces as a "Recording Failed" status in the dashboard rather than hanging silently |
| `OSError: [WinError 10048] ... port 5000` / address already in use | Another process (or a previous `python app.py` that didn't fully exit) is already bound to port 5000 | Close the other process, or find and stop it via Task Manager; the app has no built-in way to pick a different port without editing `app.py` |

---

## Current Limitations

Confirmed directly from the code, not hidden:

- **Database integration is not configured** — `/api/database/connect` is a
  hardcoded placeholder response.
- **`expected_content` and `product_to_verify` still have no dedicated
  dashboard fields** — the Replay button always calls `/api/test/run/start`
  with just `qa_url`/`recording_path`; those two fields (and
  `screenshot_threshold`/`screenshot_ignored_regions`/`screenshot_strict`)
  only work when the API is called directly.
- **Locator strategies are best-effort, not guaranteed.** All the fallback
  strategies (down to raw pixel coordinates) can still fail on a page that
  changed enough since recording, especially highly dynamic sites.
- **Navigation-chain deduplication is a timing heuristic (4.5s window),
  not a guarantee.** An unusually slow redirect chain can still produce
  two `navigate` actions instead of one for what was really a single user
  action.
- **Product validation only scans link (`<a>`) elements with plausible
  product-title-length text** (15–300 characters) and only within the same
  page the recorded actions already left the browser on — it never opens
  the site a second time or does its own search. It's a generic heuristic
  (works the same on any site), not a guaranteed-accurate product-title
  parser; short nav/category links can occasionally be miscounted as
  results.
- **`storage/searches/` and `storage/executions/` are legacy.**
  `storage/repository.py` still defines `save_search()`/`save_execution()`
  and creates both directories on startup, but no code path in the current
  project calls either function — files already in those folders are
  historical artifacts from an earlier version of the project, not
  something the current code produces. The real, currently-written replay
  result is `report.json` inside each run's own
  `generated_scripts/screenshoots/<run_id>/` folder (see
  [Screenshot Storage](#screenshot-storage)).
- **Screenshot comparison is still a deterministic pixel-sum diff, not a
  perceptual/structural comparison or an AI/vision service** — the default
  per-pixel noise floor (see [Screenshot Comparison](#screenshot-comparison))
  absorbs ordinary anti-aliasing noise, but two independent loads of a
  genuinely personalized/ad-driven page will still often register as a
  mismatch unless the differing region is masked out with
  `ignored_regions`.
- **Sites with CAPTCHAs, login walls, or heavy bot detection may not
  replay reliably** — there is no CAPTCHA-solving or login-session-reuse
  logic anywhere in this project.
- **This is a single-machine development server** (`debug=False,
  threaded=True`, bound to `127.0.0.1`) — it is not configured or intended
  to be exposed as a production service.

---

## Existing Runtime Data

If you extract this ZIP as-is, several folders already contain files from
previous runs: `storage/recordings/`, `storage/executions/` (legacy - see
[Current Limitations](#current-limitations)), `storage/searches/` (also
legacy), `generated_scripts/` (including `generated_scripts/screenshoots/`
— every past run's screenshots + `report.json`/`report.html`),
`screenshots/` (launch screenshots), and `reports/`. **These are runtime
artifacts, not part of the source code** — nothing in `app.py` or any other
module requires them to exist for the app to start; `storage/repository.py`
creates the `storage/recordings/`, `storage/executions/`, and
`storage/searches/` folders automatically on import if they're missing, and
the other folders are created the first time they're needed.

These folders will continue to **grow** the more you record and run tests:
every recording, every generated script, every test run's screenshots and
report all accumulate as separate timestamped files — nothing is cleaned up
automatically **unless you trigger it**, via `/api/maintenance/cleanup`
(see [Retention / Cleanup](#retention--cleanup)).

---

## Clean Run vs. Keeping Existing Data

You do **not** need to delete anything to start using the app fresh —
new recordings and runs simply add more timestamped files alongside the
existing ones, and the Dashboard will show everything in
`storage/recordings/`.

If you'd specifically like to start with an empty Dashboard/report history,
two options exist:

- **The built-in retention sweep** (see [Retention / Cleanup](#retention--cleanup))
  — age-based only (default 30 days) and archives by default rather than
  deleting, so it won't touch anything you made today just because you
  asked for a cleanup.
- **Manually delete everything, regardless of age** (optional, and
  **destructive** — only do this if you're sure you don't need the
  existing data):

```powershell
# WARNING: deletes all previously recorded/executed data. Source code is untouched.
Remove-Item -Recurse -Force storage\recordings\*
Remove-Item -Recurse -Force storage\executions\*
Remove-Item -Recurse -Force storage\searches\*
Remove-Item -Recurse -Force generated_scripts\*
Remove-Item -Recurse -Force reports\*
Remove-Item -Recurse -Force screenshots\*
```

None of these paths contain source code — `app.py`, `requirements.txt`,
`recorder/`, `generator/`, `executor/`, `validation/`, `storage/retention.py`,
`templates/`, `static/`, and `utils.py` are never touched by this cleanup.
