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
19. [API Reference](#api-reference)
20. [Full End-to-End Example](#full-end-to-end-example)
21. [Exact File Path Table](#exact-file-path-table)
22. [Troubleshooting](#troubleshooting)
23. [Current Limitations](#current-limitations)
24. [Existing Runtime Data](#existing-runtime-data)
25. [Clean Run vs. Keeping Existing Data](#clean-run-vs-keeping-existing-data)

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
│   └── action_capture.js         # Injected into the page to listen for DOM events
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
│   ├── recordings/               # Saved recordings (session_*.json)
│   ├── executions/                # Saved execution results (execution_*.json)
│   └── searches/                  # Legacy - see "Current Limitations"
│
├── templates/
│   ├── index.html                # Dashboard page
│   ├── recording_editor.html     # View/Edit screen for one recording
│   └── report.html               # HTML report template
│
├── static/
│   ├── js/script.js              # Dashboard JS (launch browser, list/refresh recordings)
│   └── css/style.css             # All styling
│
├── generated_scripts/            # Standalone Playwright scripts, one per recording
├── screenshots/execution_runs/   # Per-run screenshots + result.json (created by executor)
└── reports/                      # Self-contained HTML reports (report_<run_id>.html)
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

There is **no "Record" or "Stop" button** in the UI. Recording is tied
entirely to the **Launch Browser** button and the **terminal**. This is the
actual mechanism implemented in `app.py` / `recorder/record_session.py` —
here is exactly what happens, step by step:

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
   URL, page title, and a status saying *"Success - recording in terminal"*.
8. **You perform actions in the visible browser window** — click, type,
   scroll, submit, navigate, open new tabs. Every meaningful action is
   captured (see [Supported Action Types](#supported-action-types)) and
   printed live to the **terminal** running `app.py`, e.g.:
   ```
   [RECORDED] CLICK
   Element: Search Amazon
   Locator: #twotabsearchtextbox
   ```
9. **To stop recording, click into the terminal window running `python
   app.py` and press ENTER.** This is the actual, only implemented
   stop mechanism — there is no Stop button anywhere in the browser UI.
   (If the browser is closed unexpectedly instead, or a navigation gets
   permanently stuck, the recorder also detects that and stops on its own,
   logging why.)
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
| `action_type` | `click`, `dblclick`, `right_click`, `fill`, `select`, `submit`, `press`, `navigate`, or `scroll` |
| `value` | Typed text / pressed key / selected option (or `null`) |
| `locator_profile` | id, css_path, xpath, text, tag, attributes — or `null` for navigate/scroll |
| `bounding_box` | `{x, y, width, height}` at capture time — or `null` for navigate/scroll |
| `page_url` | The page the action happened on |
| `timestamp` | ISO-8601 UTC timestamp with milliseconds |

---

## Supported Action Types

Directly from `recorder/action_capture.js`, these are the action types the
recorder currently produces:

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
| `scroll` | Wheel events are accumulated and sent once, 250ms after the last wheel event ("settle on pause"), not once per wheel tick. |

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
tries these, in this exact order, stopping at the first one that finds an
element:

```
 1. data-testid
 2. data-test
 3. data-cy
 4. id
 5. name
 6. aria-label
 7. placeholder
 8. role            (Playwright get_by_role with accessible name)
 9. css_path         (id/nth-of-type chain captured at record time)
10. xpath
11. text + tag       (visible text combined with tag name)
12. bounding box     (last resort: click the recorded x/y coordinates)
```

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

**Fragile flag:** a step is flagged `fragile` (shown as amber in the HTML
report) if it only resolved via `text+tag` or `bounding_box` — these are
exactly the two strategies most likely to break the next time the page's
content or layout changes even slightly.

**Locators here are not claimed to be 100% reliable.** This is an
intentionally layered best-effort system, not a guarantee — dynamic pages,
A/B tests, and DOM structure changes can still break a replay step even
with 12 fallback strategies.

---

## Dashboard: Viewing and Editing a Recording

This is a real, working feature of the current codebase — a recording does
not have to be replayed exactly as captured. From the dashboard's "Recorded
Tests" panel, every saved recording shows as a card with **Name**, **action
count**, **saved path**, **saved time**, and a **View / Edit** button.

Clicking **View / Edit** opens `GET /recording/edit?path=...`, which loads
`templates/recording_editor.html`. That page calls `GET
/api/recordings/view?path=...` to fetch the recording's full JSON (this is
a pure read — opening a recording never modifies the original file) and
renders:

- **Metadata**: Name, Total Actions, Start URL, Recorded At, Saved At, Stop
  Reason.
- **Every action, in order**, each as its own card showing:
  - **Action Type** — editable text field
  - **Value** — editable textarea
  - **Page URL** — editable text field
  - **Locator** — read-only (shows the captured `locator_profile` as JSON)
  - **Bounding Box** — read-only (shows the captured box as JSON)
  - **Up** / **Down** buttons — reorder this action (disabled at the
    top/bottom of the list)
  - **Delete** button — removes this action

There is also an **Add Action** button at the bottom of the list, which
appends a new blank action with the minimum fields the JSON structure
needs: `action_type`, `value`, `page_url` (`locator_profile` and
`bounding_box` are set to `null` — see the note on this below).

**None of this touches the saved file on disk until you click.** All
edits/deletes/adds/reorders happen only in the browser tab's in-memory
state.

**Save Edited JSON** sends the current in-memory state to `POST
/api/recordings/save`, which writes it as a **brand-new** file — the
original recording is never overwritten. The new file is named:
```
<original_name>_edited_<YYYYMMDD_HHMMSS>.json
```
e.g. `session_20260812_121227_edited_20260813_152631.json`, saved into the
same `storage/recordings/` folder, so it shows up in the Dashboard exactly
like any other recording — including its own **View / Edit** button.

**Important, honest note about "Add Action":** the Add form only collects
`action_type`, `value`, and `page_url` — it does not let you specify a
locator or bounding box. This means a manually added `click`/`fill`/etc.
action has no real element to resolve to during replay and will generally
fail with "element not found" unless you edit the `action_type` to
`navigate` (which doesn't need a locator at all) or set the `page_url` to a
real destination. This is a genuine current limitation of the Add feature,
not a bug — see [Current Limitations](#current-limitations).

**Another honest note:** if you edit a `fill` step's value (e.g. changing a
search term) but leave a later `navigate` step untouched, that `navigate`
step still replays to the exact URL that was recorded originally. The
edited value **does** get typed and submitted — but a subsequent recorded
`navigate` action will still jump back to the old URL afterward, since
`navigate` steps are literal replays of whatever URL was captured. If you
want an edited search term to be reflected all the way to the final page,
delete or update the `navigate` step(s) that follow it too.

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
| 2 | `output_json_path` | Result JSON is not written anywhere |
| 3 | `screenshot_dir` | `generated_scripts/run_screenshots/` |
| 4 | `headless` | `"0"` — i.e. **headed** (visible) when run by hand |
| 5 | `product_name` | Not set — product validation is skipped entirely |

Running it with no arguments at all replays against the originally recorded
URL in a visible browser window, which is handy for watching a replay live.
When the dashboard triggers a replay through `/api/test/run`, it always
passes `headless="1"` (see next section) — an unattended dashboard run
never pops up a visible window.

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
Chromium replays every action against qa_url, headless
        │
        ├── screenshot per step + one final screenshot
        ▼
screenshots/execution_runs/<run_id>/result.json
        │
        ▼  (read back and interpreted by run_execution.py)
+ optional content check, screenshot diff, product validation
        │
        ├── storage/executions/execution_<run_id>.json
        └── validation/report_generator.py -> reports/report_<run_id>.html
```

The endpoint that drives this whole pipeline is:

```
POST /api/test/run
```

**Request fields**, read directly from `app.py`:

| Field | Required | Purpose |
|---|---|---|
| `qa_url` | Yes | The target site to replay against |
| `recording_path` | No | Which saved recording to replay; if omitted, an empty/no-op test case is used |
| `expected_content` | No | Text that must appear on the final page for the run to pass |
| `expected_screenshot` | No | Path to a baseline PNG to diff the final screenshot against |
| `product_to_verify` | No | A product name to look for on whatever page replay ends on |

**Important distinction — this is an API without a UI button.** The
current dashboard (`templates/index.html` / `static/js/script.js`) does
**not** call `/api/test/run` anywhere. There is no "Run Test" button, no
QA URL field, no expected-content field, and no product-to-verify field in
the current UI. This endpoint exists and works, and is fully exercised by
the Dashboard→Editor→Save pipeline described above, but it is currently
**backend/API-only** — to run it you call it directly (`curl`, Postman,
your own script), for example:

```powershell
curl -X POST http://127.0.0.1:5000/api/test/run ^
  -H "Content-Type: application/json" ^
  -d "{\"qa_url\": \"https://your-qa-site.com\", \"recording_path\": \"storage/recordings/session_20260812_131205.json\"}"
```

Response fields: `status` (`PASS`/`FAIL`), `message`, `html_report` (path),
`json_report` (path).

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

From `executor/run_execution.py`:

```python
RUNS_DIR = BASE_DIR / "screenshots" / "execution_runs"
```

Each `/api/test/run` call creates one folder, named after the run's
timestamp:
```
screenshots/execution_runs/<run_id>/
```
Real example:
```
screenshots/execution_runs/20260812_130826/
```

Inside that folder:

| File | Contents |
|---|---|
| `step1.png`, `step2.png`, ... | One screenshot taken right after each recorded action replays |
| `final.png` | Full-page screenshot after the last action |
| `product_validation.png` | Only present if a `product_to_verify` was requested |
| `result.json` | The raw result written by the generated script itself (steps, final_url, final_text, final_screenshot, product_validation) — this is the file `run_execution.py` reads back and reshapes into the execution result described next |

---

## Execution JSON

From `storage/repository.py`:

```python
EXECUTIONS_DIR = BASE_DIR / "storage" / "executions"
```

```
storage/executions/execution_<YYYYMMDD_HHMMSS>.json
```
Real example:
```
storage/executions/execution_20260812_130839.json
```

**Actual top-level fields** (verified against a real saved file):

| Field | Meaning |
|---|---|
| `status` | `PASS` or `FAIL` (overall — see below for what counts) |
| `message` | Human-readable summary, e.g. `"all steps resolved and validations passed"` or `"steps failed: [5]; UI elements missing at steps: [5]"` |
| `qa_url` | The URL that was actually replayed against |
| `steps` | Every replayed action: `index`, `action_type`, `strategy_used`, `element_found`, `success`, `error`, `screenshot`, `fragile` |
| `ui_elements` | One entry per non-navigate/scroll step: `index`, `action_type`, `element_found`, `locator_used`, `status`, `message` |
| `ui_elements_status` | `PASS` if every UI element resolved, else `FAIL` |
| `content_check` | `true`/`false` if `expected_content` was requested, else `null` |
| `screenshot_diff` | `{match, diff_ratio, note}` if `expected_screenshot` was requested, else `null` |
| `product_validation` | Full product-search result if `product_to_verify` was requested, else `null` |
| `final_screenshot` | Path to the full-page final screenshot |
| `run_id` | The same timestamp used for the screenshot folder name |

**Overall `status` is `PASS` only if all of these hold:** every step
succeeded, every UI element resolved, content check didn't explicitly fail,
screenshot diff didn't explicitly mismatch, and (if requested) the product
was found.

---

## HTML Report

```
Execution result (the dict above)
        │
        ▼
validation/report_generator.py  ->  generate_report()
        │
        ▼
reports/report_<run_id>.html
```
Real example:
```
reports/report_20260812_130826.html
```

Every screenshot referenced by the result is **embedded directly into the
HTML as a base64 `data:image/png;base64,...` URI** — the report is a single
file with no external dependencies; you can email it or open it from
anywhere without also handing over the `screenshots/` folder.

**Sections actually present in `templates/report.html`** (verified — this
is the complete list, in order):

1. **Overall banner** — PASS/FAIL + the message
2. **Validations** — Expected Content Found (pill), Screenshot Diff (pill
   with ratio, or "not requested"/"skipped")
3. **Product Validation** — only rendered if a product was requested:
   PASS/FAIL banner, Requested Product, Found (Yes/No), Match Type (EXACT
   MATCH / POSSIBLE-SIMILAR MATCH / -), Position + Product Title + Product
   URL if found, or Reason + Results Checked if not, plus an embedded
   evidence screenshot
4. **Execution** — Total Steps, Passed, Failed, First Failed Step
5. **Steps** — a table: index, action, locator strategy used, PASS/FAIL,
   amber "fragile" tag if applicable, error text
6. **UI Elements** — a table of which elements were found/not found
7. **Screenshots** — every step screenshot plus the final full-page
   screenshot

---

## Screenshot Comparison

From `validation/compare.py`:

```python
DEFAULT_THRESHOLD = 0.02  # fraction of max possible pixel difference
```

- Resizes the actual screenshot to match the baseline's dimensions if they
  differ, then computes the sum of per-pixel RGB differences as a fraction
  of the maximum possible difference.
- `match: true` if `diff_ratio <= 0.02`, else `false`.
- **If the baseline screenshot doesn't exist on disk:** the comparison is
  **skipped**, not failed — `{match: null, diff_ratio: null, note: "baseline
  screenshot not found at ..., skipped"}`. This does not fail the overall
  run.
- **If no actual screenshot was captured from the run:** similarly skipped
  with a `note` explaining why, not treated as a hard failure.
- This is a blunt pixel-sum diff, not a perceptual/structural comparison —
  it's good enough to catch a badly broken layout, not a fine-grained visual
  regression tool.

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

## API Reference

Every route below is taken directly from `app.py` — nothing here is
invented, and nothing implemented in `app.py` is omitted.

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/` | Renders the Dashboard (`index.html`) |
| GET | `/api/recordings` | Lists all saved recordings for the Dashboard panel |
| GET | `/recording/edit?path=...` | Renders the Recording Editor page for one recording |
| GET | `/api/recordings/view?path=...` | Returns one recording's full JSON (used by the editor page) |
| POST | `/api/recordings/save` | Saves the edited recording as a new `*_edited_<timestamp>.json` file |
| POST | `/api/browser/launch` | Launches a browser, navigates, and starts recording (body: `{"url": "..."}`) |
| GET | `/api/database/connect` | Always returns "not configured" — placeholder only |
| GET | `/status` | Current session state: `flask`, `playwright_installed`, `browser_active`, `recording`, `current_url` |
| POST | `/api/test/run` | Generates + replays a script against a QA URL and produces a report (API-only — no UI button calls this) |

---

## Full End-to-End Example

Only steps actually supported by the current code/UI/API are listed.

**Recording (via the Dashboard UI):**
1. Enter a production-like URL, click **Launch Browser**.
2. Perform your actions in the opened window (click, fill, submit,
   navigate, scroll — whatever the real flow is).
3. Click into the `app.py` terminal, press **ENTER** to stop.
4. JSON is saved to `storage/recordings/`, and a script is generated to
   `generated_scripts/` automatically.

**Optional — editing before replay (via the Dashboard UI):**
5. Refresh the dashboard, click **View / Edit** on the new card.
6. Modify field values, delete unwanted steps, add minimal new steps,
   reorder with Up/Down.
7. Click **Save Edited JSON** — a new file appears in
   `storage/recordings/` and in the Dashboard list.

**Replaying against QA (via the API — no UI button for this today):**
8. `POST /api/test/run` with `qa_url` set to your QA/staging URL and
   `recording_path` pointing at either the original or the edited JSON.
9. The existing generator turns that JSON into a script (again, or reuses
   the one from step 4/7 if you generated it yourself).
10. The existing executor runs that script as a subprocess against
    `qa_url`, headless, capturing a screenshot per step plus a final
    screenshot.
11. `storage/executions/execution_<run_id>.json` is written.
12. `reports/report_<run_id>.html` is generated with everything embedded.
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
| Script generator | `generator/script_generator.py` |
| Executor | `executor/run_execution.py` |
| Screenshot comparison | `validation/compare.py` |
| Report generator | `validation/report_generator.py` |
| Storage (single source of truth for disk I/O) | `storage/repository.py` |
| Saved recordings | `storage/recordings/` |
| Saved execution results | `storage/executions/` |
| Legacy/unused search results | `storage/searches/` |
| Generated Playwright scripts | `generated_scripts/` |
| HTML reports | `reports/` |
| Per-run execution screenshots | `screenshots/execution_runs/` |
| Dashboard template | `templates/index.html` |
| Recording editor template | `templates/recording_editor.html` |
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
| Recording not saved / no JSON appears | You closed the terminal or killed the process before pressing ENTER | Always press ENTER in the `app.py` terminal to stop cleanly; an unexpected browser close is still auto-saved, but killing the whole Python process is not |
| Generated script fails immediately with a Python error | The recording JSON is malformed, or was hand-edited into invalid JSON via `/api/recordings/save` with something odd in the body | Re-open the file in the Recording Editor to check it loads without an error, or inspect the raw JSON in `storage/recordings/` |
| `/api/test/run` returns `"the test script didn't complete - couldn't reach the QA URL or it crashed"` | The generated script's subprocess didn't produce a `result.json` — often a bad `qa_url`, or the script hit the 120-second timeout | Check `screenshots/execution_runs/<run_id>/` for partial output; try running the generated script directly (see [Generated Script](#generated-script)) to see the real Playwright error |
| Report not generated | `execute_test()` itself raised before `generate_report()` was reached, or the request never reached `/api/test/run` (e.g. wrong method/body) | Check the Flask terminal for a traceback; confirm the request is `POST` with a JSON body containing `qa_url` |
| Screenshot missing in report | The step's screenshot capture failed (page in a bad state) or the baseline path in `expected_screenshot` doesn't exist | The report shows "skipped" for a missing baseline rather than failing outright; check `screenshots/execution_runs/<run_id>/` directly for what was actually captured |
| `execution_*.json` / recording JSON missing after a run | The run crashed before `repository.save_execution()` / `repository.save_recording()` was reached | Check the Flask/terminal logs for the actual exception |
| `OSError: [WinError 10048] ... port 5000` / address already in use | Another process (or a previous `python app.py` that didn't fully exit) is already bound to port 5000 | Close the other process, or find and stop it via Task Manager; the app has no built-in way to pick a different port without editing `app.py` |

---

## Current Limitations

Confirmed directly from the code, not hidden:

- **Recording stop depends entirely on pressing ENTER in the terminal.**
  There is no Stop button in the browser UI.
- **Database integration is not configured** — `/api/database/connect` is a
  hardcoded placeholder response.
- **`/api/test/run` (the actual QA replay endpoint) has no UI trigger** in
  the current dashboard. It works and is fully covered by tests, but you
  must call it directly (curl/Postman/your own script) — there's no "Run
  Test" button, QA URL field, or product-to-verify field on screen today.
- **Added actions in the Recording Editor have no locator/bounding box.**
  A manually added `click`/`fill`/etc. step will almost always fail to
  resolve an element during replay, since the Add form only collects
  `action_type`, `value`, and `page_url`. Adding a `navigate` step (which
  needs no locator) works reliably; adding anything else generally
  requires also hand-editing the JSON's `locator_profile`.
- **Editing a `fill` value doesn't retroactively change a later recorded
  `navigate` step's URL.** If your recording searches for something and
  then has a `navigate` step, editing the search term still submits the
  new value, but a subsequent `navigate` step will replay to the
  originally-recorded URL, not wherever the new search would have landed.
- **Locator strategies are best-effort, not guaranteed.** All 12 fallback
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
- **`storage/searches/` is legacy.** `storage/repository.py` still defines
  `save_search()` and creates this directory on startup, but no code path
  in the current project calls it — the files already in that folder are
  historical artifacts from an earlier version of the project, not
  something the current code produces.
- **Screenshot comparison is a blunt pixel-sum diff**, not a perceptual or
  structural comparison — it will flag legitimately different-but-similar
  pages (e.g. two independent loads of a personalized/ad-driven page) as a
  mismatch just as readily as it flags a real regression.
- **Sites with CAPTCHAs, login walls, or heavy bot detection may not
  replay reliably** — there is no CAPTCHA-solving or login-session-reuse
  logic anywhere in this project.
- **This is a single-machine development server** (`debug=False,
  threaded=True`, bound to `127.0.0.1`) — it is not configured or intended
  to be exposed as a production service.

---

## Existing Runtime Data

If you extract this ZIP as-is, several folders already contain files from
previous runs: `storage/recordings/`, `storage/executions/`,
`storage/searches/`, `generated_scripts/`, `reports/`,
`screenshots/execution_runs/`. **These are runtime artifacts, not part of
the source code** — nothing in `app.py` or any other module requires them
to exist for the app to start; `storage/repository.py` creates the
`storage/recordings/`, `storage/executions/`, and `storage/searches/`
folders automatically on import if they're missing, and the other folders
are created the first time they're needed.

These folders will continue to **grow** the more you record and run tests:
every recording, every generated script, every test run's screenshots,
execution JSON, and HTML report all accumulate as separate timestamped
files — nothing is cleaned up automatically.

---

## Clean Run vs. Keeping Existing Data

You do **not** need to delete anything to start using the app fresh —
new recordings and runs simply add more timestamped files alongside the
existing ones, and the Dashboard will show everything in
`storage/recordings/`.

If you'd specifically like to start with an empty Dashboard/report history
(optional, and **destructive** — only do this if you're sure you don't need
the existing data):

```powershell
# WARNING: deletes all previously recorded/executed data. Source code is untouched.
Remove-Item -Recurse -Force storage\recordings\*
Remove-Item -Recurse -Force storage\executions\*
Remove-Item -Recurse -Force storage\searches\*
Remove-Item -Recurse -Force generated_scripts\*
Remove-Item -Recurse -Force reports\*
Remove-Item -Recurse -Force screenshots\execution_runs\*
```

None of these paths contain source code — `app.py`, `requirements.txt`,
`recorder/`, `generator/`, `executor/`, `validation/`, `templates/`,
`static/`, and `utils.py` are never touched by this cleanup.
