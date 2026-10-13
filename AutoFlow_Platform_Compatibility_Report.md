# AutoFlow QA - Platform Compatibility Report

Date: 13 October 2026. This was a read-only analysis: nothing in the project was changed, installed or run.

**Evidence sources**

- Project files.
- Installed package metadata in `venv/` (`*.dist-info`).
- Playwright's own driver files (`browsers.json`, `hostPlatform.js`, `registry/index.js`).
- The official Playwright docs at the **v1.47.0 tag** (`docs/src/intro-python.md`).
- PyPI release file lists (`pypi.org/pypi/<pkg>/<ver>/json`).
- Read-only commands on this Mac.

Anything not proven this way is marked **UNVERIFIED**.

---

## 0. Key findings first

1. **`pip install -r requirements.txt` fails on every new machine, Windows or macOS.**
   - The last line of `requirements.txt` is `python==3.12`. pip reads that as a package named `python`, and PyPI has no such project (`https://pypi.org/pypi/python/json` returns HTTP 404).
   - pip resolves all requirements before installing any, so **nothing** gets installed. Expect `No matching distribution found for python==3.12`.
   - This machine works only because its `venv` already existed.
   - Fix (not applied, read-only): delete that line and state the Python version in the README instead.
2. **The project uses Playwright 1.47.0, not the current Playwright.**
   - The "baseline" in the question (Windows 11+, macOS 14+) is the requirement of **current** Playwright.
   - Playwright **1.47.0** officially requires:
     - "Python 3.8 or higher";
     - "Windows 10+, Windows Server 2016+ or Windows Subsystem for Linux (WSL)";
     - "macOS 13 Ventura, or macOS 14 Sonoma".

     (Source: `microsoft/playwright` v1.47.0 `docs/src/intro-python.md`.)
3. **Python 3.13 and newer cannot be used with the current pins.**
   - Playwright 1.47.0 pins `greenlet ==3.0.3`, and greenlet 3.0.3 publishes **no cp313 wheel**.
4. **Python 3.8 cannot be used either.**
   - `app.py:2246` uses `-> list[Path]`, which is evaluated when the function is defined and needs Python 3.9.
   - `watchdog==6.0.0` requires Python ≥ 3.9.
5. **On macOS, port 5000 is shared with AirPlay Receiver.**
   - On this Mac, `ControlCenter` listens on `*:5000` (IPv4 and IPv6), next to the app on `127.0.0.1:5000`.
   - `http://127.0.0.1:5000` reaches the app.
   - `http://localhost:5000` can reach AirPlay instead (**UNVERIFIED** in a browser).

---

## 1. Part 1 - What the project actually uses

### 1.1 Dependencies

**Third-party imports in the code the app loads:**

| Import | Where |
|---|---|
| `flask` | `app.py:42` |
| `playwright` | `app.py:43`, `recorder/pick_element.py:69`, generated replay scripts |
| `watchdog` | `app.py:48-49` |
| `PIL` (Pillow) | `validation/compare.py:33` |
| `jinja2` | `validation/report_generator.py:14` |

All five are listed in `requirements.txt`; nothing the app imports is missing from it. The scan covered `app.py`, `utils.py`, `regenerate.py`, `executor/`, `generator/`, `recorder/`, `storage/*.py` and `validation/`, excluding `venv`, backups and test fixtures.

**Installed packages:**

| Package | In requirements.txt | Installed | Pinned | Requires-Python (installed metadata) |
|---|---|---|---|---|
| Flask | `Flask==3.0.3` | 3.0.3 | yes | ≥ 3.8 |
| playwright | `playwright==1.47.0` | 1.47.0 | yes | ≥ 3.8 |
| Pillow | `Pillow==10.4.0` | 10.4.0 | yes | ≥ 3.8 |
| Jinja2 | `Jinja2==3.1.6` | 3.1.6 | yes | ≥ 3.7 |
| watchdog | `watchdog==6.0.0` | 6.0.0 | yes | **≥ 3.9** |
| Werkzeug | (via Flask: `Werkzeug>=3.0.0`) | 3.1.9 | **no** | ≥ 3.9 |
| click | (via Flask: `click>=8.1.3`) | 8.5.0 | **no** | **≥ 3.10** (pip picks an older click on 3.9) |
| itsdangerous | (via Flask) | 2.2.0 | no | ≥ 3.8 |
| blinker | (via Flask) | 1.9.0 | no | ≥ 3.9 |
| MarkupSafe | (via Jinja2/Werkzeug) | 3.0.4 | no | ≥ 3.9 |
| greenlet | (via playwright: `greenlet ==3.0.3`) | 3.0.3 | yes (by playwright) | ≥ 3.7, but wheels only for cp37-cp312 |
| pyee | (via playwright: `pyee ==12.0.0`) | 12.0.0 | yes (by playwright) | ≥ 3.8 |
| typing_extensions | (via pyee) | 4.16.0 | no | ≥ 3.9 |
| `python==3.12` | listed | - | - | **invalid requirement** (see 0.1) |

**Wheel availability on PyPI** (this decides what installs without a compiler):

**greenlet 3.0.3**

| | macOS | Windows |
|---|---|---|
| Python 3.10-3.12 | `macosx_11_0_universal2` | `win_amd64` only (no 32-bit) |
| Python 3.7-3.9 | `macosx_11_0_universal2` | `win32` and `win_amd64` |
| Python 3.13 | none | none |
| Windows ARM64 | - | none |

**playwright 1.47.0**

- macOS: `macosx_10_13_x86_64`, `macosx_11_0_arm64`, `macosx_11_0_universal2`.
- Windows: `win32`, `win_amd64`.
- No `win_arm64` wheel.

**Pillow 10.4.0**

- Wheels for cp38-cp313, including `cp312 win_arm64` and `cp313 macosx_11_0_arm64` / `macosx_10_13_x86_64`.

**watchdog 6.0.0**

- macOS wheels for cp39-cp313: `macosx_10_9`/`10_13` x86_64, `11_0_arm64` and universal2.
- Windows: `py3 win32` / `win_amd64`.

### 1.2 Playwright

**Versions**

| Item | Value | Evidence |
|---|---|---|
| Installed Playwright | **1.47.0** | `python -m playwright --version`; the playwright dist-info |
| Bundled Chromium | **129.0.6668.29**, revision **1134** | `driver/package/browsers.json` |
| Installed browser cache | `~/Library/Caches/ms-playwright/chromium-1134` (428 MB) and `ffmpeg-1010` | `du` |
| Playwright driver | Node **v20.17.0**, arm64 binary | `driver/node --version`; `file` |

**What the code launches**

- **Bundled Chromium only**: `pw.chromium.launch(headless=…)`, with no `channel=` and no `executable_path` anywhere. Launch sites:
  - `app.py:520`, `:531`, `:1497`, `:1504`, `:1669`, `:1672`;
  - `recorder/pick_element.py:1038`, `:1225`;
  - the replay template, `generator/script_generator.py:22046`.
- Google Chrome and Microsoft Edge are **not** needed. Firefox and WebKit are never used.
- A headed replay asks for `--window-position=0,0 --window-size=1280,900` and falls back to headless when no display exists (`script_generator.py:22043-22052`).

**Official OS requirements of this exact version (v1.47.0 docs)**

- Windows 10+, Windows Server 2016+ or WSL.
- macOS 13 Ventura, or macOS 14 Sonoma.
- Python 3.8+.

**How Playwright 1.47 picks a browser build** (`driver/package/lib/utils/hostPlatform.js`, `registry/index.js`):

- **macOS 11-14:** its own build ("mac11" … "mac14").
- **macOS 15 and newer:** clamped to **mac14** (`LAST_STABLE_MAC_MAJOR_VERSION = 14`), so macOS 15 and 26 get the macOS 14 Chromium build.
- **Apple Silicon:** detected by CPU model "Apple", which gives the `-arm64` build.
- **Windows:** only a **win64 (x64)** Chromium build exists; there is no Windows ARM64 build.

### 1.3 Server side

- Flask 3.0.3 (Python ≥ 3.8).
- Werkzeug 3.1.9 (unpinned, Python ≥ 3.9).
- Jinja2 3.1.6.
- `app.run(host="127.0.0.1", port=5000, debug=False, threaded=True)` (`app.py:3900-3905`).
- watchdog 6.0.0 watches the recordings folder (`app.py:48`).

---

## 2. Part 2 - Minimum Python version the code needs

**Syntax**

- Every file the app loads, including a **generated replay script** built from `SCRIPT_TEMPLATE`, was parsed at each Python grammar version.
- **All of them parse as Python 3.7.**
- None of these features appear: `match`/`case`, `except*`, parenthesised context managers, 3.12-only f-strings.

**Runtime features**

- **Highest requirement:** `app.py:2246`, `def _get_image_files(folder: Path, recursive=False) -> list[Path]:`.
  - There is no `from __future__ import annotations`, so on Python 3.8 importing `app.py` raises `TypeError: 'type' object is not subscriptable`.
  - **The code minimum is therefore Python 3.9.**
- `datetime.fromisoformat` (`app.py:3294`, `:3696`; `recorder/record_session.py:98`) only parses strings written by Python's own `isoformat()`, or ones with `Z` replaced first. They work on 3.9 and 3.10, which accept only that format.
- No use of `removeprefix`/`removesuffix`, `zoneinfo`, dict `|` merge, `tomllib`, `ExceptionGroup`, `Self` or 3.12-only standard-library calls.

**Things removed in newer Python**

- None of the modules removed in 3.12 or 3.13 are used: `distutils`, `imp`, `cgi`, `pipes`, `telnetlib`, `asyncore`, `crypt`, `imghdr`, and so on.
- **Future risk:** `generator/script_generator.py` (and the scripts it generates) contains non-raw strings with `\d` / `\s`.
  - Examples: `script_generator.py:1601`; generated-script lines with `/\s+/` and `/\d/` inside JavaScript strings.
  - Python 3.12+ prints `SyntaxWarning: invalid escape sequence` for them (seen in `replay_console.txt` stderr). They still work.
  - CPython has announced these will eventually become errors. **UNVERIFIED** in which version.

**Dependency floors**

- watchdog 6.0.0, Werkzeug 3.1 and MarkupSafe 3.0 need **≥ 3.9**.
- greenlet 3.0.3 has wheels only up to **3.12**.

**Python verdict:** minimum 3.9, maximum 3.12 (with the current pins).

---

## 3. Part 3 - OS-specific code and assumptions

| # | Item | Evidence | Affects |
|---|---|---|---|
| 1 | Replay runs as a separate process using the project venv's Python: `venv\Scripts\python.exe` on Windows, `venv/bin/python` elsewhere, falling back to `sys.executable` | `executor/run_execution.py:218-223` | Correct on Windows and macOS. A venv copied from another machine with broken interpreter links falls back to whatever Python started the app. |
| 2 | Subprocess launched with an argument list (no shell), `encoding="utf-8", errors="replace"` | `run_execution.py:499`, `:623-624` | Safe with spaces in paths (this project lives in `claude 6/` and works). |
| 3 | Server bound to `127.0.0.1:5000`, no setting to change it | `app.py:3900-3905` | **macOS 12+:** AirPlay Receiver (`ControlCenter`) also listens on 5000; on this Mac on `*:5000` IPv4 and IPv6, beside the app. **Windows:** another program on 5000 gives `WinError 10048` (README troubleshooting already notes it). |
| 4 | `localhost` vs `127.0.0.1` | README tells users `http://127.0.0.1:5000` (README:209, :219) | On macOS, `localhost` may resolve to IPv6 `::1`, which only AirPlay listens on, so the page could show AirPlay's 403. **UNVERIFIED** in a browser. |
| 5 | Live log opened as a browser popup (`window.open('/logs…')`) | `static/js/script.js:1678-1682` | Any OS; a popup blocker only hides the window (progress still works). |
| 6 | Paths: `pathlib` throughout; report paths normalised with `.replace("\\", "/")` | e.g. `app.py:496`, `run_execution.py:138` | Windows-safe. |
| 7 | Long file names: run folders and screenshot names reach **188 characters** relative to the project folder | longest path found under `storage/generated_scripts/screenshoots/…` | **Windows** without long-path support (260-character limit): risky if the project sits in a deep folder such as OneDrive. **UNVERIFIED** where exactly it fails. |
| 8 | Select-all key uses Playwright's `ControlOrMeta+A` (Cmd on macOS, Ctrl elsewhere) | `script_generator.py:3962` | Correct on both. `ControlOrMeta` exists in Playwright ≥ 1.45. |
| 9 | Text encoding: files read and written with `encoding="utf-8"`; the replay script switches its output streams to UTF-8 | `script_generator.py:92`; many `encoding="utf-8"` calls | Windows consoles with cp1252 code pages are handled. |
| 10 | Screen scale: recordings store `devicePixelRatio`, viewport, user agent, locale and timezone, and the replay context reuses them | `record_session.py:68`; template `new_context(viewport, device_scale_factor, user_agent, locale, timezone_id)` | A recording from a Retina Mac (scale 2) replayed on a Windows PC at 125-150% is emulated, so the layout matches the recording. But the replayed site sees the **recording machine's** user agent, locale and timezone. |
| 11 | Headed window size fixed at 1280×900 at position 0,0 | `script_generator.py:22045` | Screens shorter than about 900 px (1366×768 laptops, or 1920×1080 at 150% = 1280×720 logical) will cut off part of the window. The page viewport is unaffected. **UNVERIFIED** visually. |
| 12 | Headed launch falls back to headless with no display | `script_generator.py:22047-22052` | Windows Server / WSL without a GUI: replay still runs. The **recorder and Pick Element need a visible browser** (`headless=False` paths in `app.py` / `pick_element.py`), so recording needs a desktop session. |
| 13 | macOS file watching uses native FSEvents (`_watchdog_fsevents…darwin.so`) | installed watchdog binary | Needs a native wheel matching the Mac's architecture (see Part 4). |

---

## 4. Part 4 - Hardware and architecture

### 4.1 Apple Silicon vs Intel Macs

**Architecture-specific pieces in this venv**

- `venv/bin/python3.12` is a symlink to `/opt/homebrew/opt/python@3.12/bin/python3.12`, the **Apple Silicon Homebrew** location.
- Native wheels installed:

| Package | Wheel tag |
|---|---|
| Pillow | `macosx_11_0_arm64` |
| MarkupSafe | `macosx_11_0_arm64` |
| watchdog | `macosx_11_0_arm64` |
| greenlet | `macosx_11_0_universal2` (arm64 and x86_64) |

- The Playwright driver Node binary is arm64. The Chromium cache is the `mac-arm64` build.

**What follows**

- This `venv` will **not** work if it is copied to an Intel Mac or to a Mac without Homebrew Python 3.12 at the same path. It will not work on Windows either. Every machine must build its own venv.
- Both architectures are supported when installed natively:
  - Playwright 1.47 ships `macosx_11_0_arm64` and `macosx_10_13_x86_64` wheels, plus Chromium `mac-arm64` and `mac` builds;
  - greenlet ships `universal2`.
- **Rosetta risk (UNVERIFIED):** on an Apple Silicon Mac running an x86_64 Python, Playwright still picks the arm64 Chromium (it detects the CPU model, not the process architecture). That mix is untested.

### 4.2 Windows on ARM

- Playwright 1.47.0 has **no `win_arm64` wheel**, greenlet 3.0.3 has **no `win_arm64` wheel**, and the Chromium build is **win64 (x64) only**.
- So native ARM64 Python cannot install the project.
- **x64 Python under Windows 11's x64 emulation** should install and run it. That route is **UNVERIFIED** and unofficial.

### 4.3 Resources

What runs at the same time:

- the Flask app (one Python process);
- one replay subprocess with its own headed Chromium;
- during recording, the recorder's headed Chromium;
- during Pick Element, another Chromium.

So up to **two Chromium instances plus two Python processes** run together.

| Item | Measured / estimated |
|---|---|
| venv | 139 MB (measured) |
| Chromium 129 + ffmpeg cache | 431 MB (measured) |
| `storage/` | 570 MB, of which recordings are 12 MB for 72 recordings (measured) |
| `generated_scripts/` | 936 MB (screenshots 792 MB for 330 runs, about 2.4 MB per run; single runs measured 4.2-7.0 MB) |
| `backups/` | 1.3 GB (old copies) |
| RAM | **Estimate (UNVERIFIED):** each headed Chromium with a modern site uses about 300-800 MB, Python processes about 100-200 MB each. Two browsers on heavy sites need about 2-3 GB on top of the OS. |
| CPU | Screenshot comparison (Pillow) and two browsers: 4 cores comfortable. This Mac has 10 (Apple M4). |

---

## 5. Part 5 - This machine

| Item | Value | Meets…? |
|---|---|---|
| OS | macOS **15.6.1** (build 24G90) | Playwright 1.47 lists only macOS 13-14, so this is **not officially listed**; it runs on the macOS 14 browser build and has been used for many runs. Current Playwright baseline (macOS 14+): yes. |
| Architecture | **arm64**, Apple M4, 10 CPU cores | yes |
| RAM / disk | 16 GB / 253 GB free of 460 GB | yes |
| Python | **3.12.15** (Homebrew, arm64) | yes (3.9-3.12 range) |
| Playwright | 1.47.0, Chromium 129.0.6668.29 installed (`chromium-1134`) | yes |
| Port 5000 | AirPlay (`ControlCenter`) on `*:5000`, the app on `127.0.0.1:5000` | works because the app is opened via `127.0.0.1` |

The README's own requirements table says "Python 3.12.7" and "Built and tested on Windows" (README:114, :120). It has Windows setup steps only and no macOS setup section.

---

## 6. Final tables

### 6.1 Windows

| Level | Versions | Evidence / reason |
|---|---|---|
| **Not supported** | Windows 7, 8, 8.1; any 32-bit Windows; 32-bit Python 3.10+ | Playwright 1.47 requires Windows 10+. The only Chromium build is win64. greenlet 3.0.3 has no `win32` wheel for cp310+. |
| **Works but unofficial** | Windows 11 **on ARM**, using **x64** Python under emulation (**UNVERIFIED**) | No `win_arm64` wheels for playwright or greenlet, and Chromium is x64 only. |
| **Works but unofficial** | WSL2 (officially listed by Playwright 1.47) | Replay is fine headless. The recorder and Pick Element need a visible browser, which needs WSLg on Windows 11. **UNVERIFIED.** |
| **Supported (minimum)** | **Windows 10 64-bit** (22H2), Windows Server 2016+, with 64-bit Python 3.9-3.12 | Playwright 1.47 docs list "Windows 10+, Windows Server 2016+". Note: Microsoft ended mainstream Windows 10 support in October 2025. The tool still runs, but the OS gets no updates. |
| **Recommended** | **Windows 11 (23H2 / 24H2) x64**, Python **3.12** 64-bit, 16 GB RAM | Supported by both Playwright 1.47 and current Playwright. The README is written and tested for Windows. |
| **Best** | Windows 11 24H2 x64; Python 3.12 (python.org, 64-bit); 16 GB+ RAM; SSD; screen ≥ 1920×1080 at 100-125% scaling; project in a short path (for example `C:\autoflow`) or long paths enabled | Fits the 1280×900 headed window. Avoids the 260-character path limit. Python 3.12 is the version the README targets. |

### 6.2 macOS

| Level | Versions | Evidence / reason |
|---|---|---|
| **Not supported** | macOS **10.15 Catalina and older** | greenlet 3.0.3 and Pillow/watchdog/MarkupSafe arm64 wheels need `macosx_11_0`. Playwright 1.47's Chromium 129 lists macOS 13+ officially. Apple Silicon needs macOS 11+ anyway. |
| **Works but unofficial** | macOS **11 Big Sur, 12 Monterey** | Playwright 1.47 still has `mac11` / `mac12` (and `-arm64`) Chromium builds, but the docs list only 13 and 14. Python 3.12 runs there. **UNVERIFIED** end to end. |
| **Supported (minimum)** | **macOS 13 Ventura** (Intel or Apple Silicon) | Listed in the Playwright 1.47 docs. |
| **Recommended** | **macOS 14 Sonoma** | Listed by Playwright 1.47 **and** meets current Playwright's minimum. |
| **Best** | macOS 14 Sonoma (officially listed) or macOS **15 Sequoia** (this machine: proven by many runs, but not listed for Playwright 1.47; it uses the macOS 14 browser build), on Apple Silicon with 16 GB RAM and Python 3.12 | This machine is the only real-world evidence. **macOS 26 Tahoe** also maps to the macOS 14 build, but is **UNVERIFIED**. |

**Apple Silicon vs Intel**

- Both are supported **when the venv is created on that Mac** (Section 4.1).
- Intel Macs: macOS 13-15 depending on the model. Apple's own model limits apply (**UNVERIFIED** per model).
- Apple Silicon: macOS 13+ recommended.

### 6.3 Python

| Level | Versions | Evidence |
|---|---|---|
| **Not supported** | **≤ 3.8** | `app.py:2246` `-> list[Path]` fails at import on 3.8; `watchdog==6.0.0` requires ≥ 3.9. |
| **Minimum** | **3.9** | All pins have wheels for 3.9; `click` falls back to 8.1.x. Untested. Python 3.9 itself reached end of life in October 2025, so not advised. |
| **Supported** | **3.10, 3.11** | All pins have wheels (greenlet macOS universal2 / Windows `win_amd64`). Untested here. |
| **Recommended** | **3.12** (64-bit) | This machine runs 3.12.15; the README says 3.12.7; every pinned package has cp312 wheels for macOS and Windows x64. |
| **Risky / not supported (too new)** | **3.13, 3.14** | greenlet 3.0.3 (pinned exactly by playwright 1.47.0) has **no cp313 wheel**. pip would try to compile it, and greenlet 3.0.x predates 3.13 support, so it is expected to fail (**UNVERIFIED** compile result). Homebrew and python.org now install 3.13+ by default (**UNVERIFIED** for each installer), so new machines often get it. |

### 6.4 Hardware

| | Minimum | Recommended |
|---|---|---|
| CPU | 2 cores, x64 or Apple Silicon (64-bit) | 4+ cores |
| RAM | 8 GB (estimate: two browsers plus app) | 16 GB |
| Disk | about 1 GB free for venv + Chromium, plus about 5 MB per replay run | 10 GB+ free on an SSD (runs and backups grow: about 2.8 GB here today) |
| Screen | 1366×768 (the headed browser window may be cut off) | 1920×1080 at 100-125% scaling |
| Other | A desktop session (recording and Pick Element need a visible browser); internet access to download Chromium once | |

---

## 7. What can still fail on a machine that meets the official requirements (ranked by risk)

1. **`requirements.txt` contains `python==3.12`**, so `pip install -r requirements.txt` installs nothing (verified: no such PyPI project). This is **certain** on every fresh Windows or macOS setup.
2. **Python 3.13 or 3.14 installed** (now the default from most installers): greenlet 3.0.3 has no wheel, so install fails.
3. **A venv copied from another machine**: interpreter symlinks and arm64-only native packages break on Intel, on a Mac without the same Homebrew path, or on Windows.
4. **`playwright install chromium` not run** (the browser lives in the user cache, not in the project): `Executable doesn't exist`.
5. **macOS port 5000 / AirPlay**: opening `localhost:5000` may reach AirPlay (**UNVERIFIED**). Another app on 5000 on Windows (`WinError 10048`). No setting exists to change the port.
6. **macOS 15+ / Windows 11 24H2+ with Playwright 1.47**: not in 1.47's official list (it predates them). Works on this macOS 15 machine; other combinations are **UNVERIFIED**.
7. **Windows path length**: up to about 188 characters inside the project, plus the project path, can exceed 260 characters in deep or OneDrive folders.
8. **Replaying a recording from another machine**: it uses the recorder's user agent, locale, timezone and scale. A site may show a different layout or language (**UNVERIFIED** per site).
9. **Small or highly scaled screens**: the fixed 1280×900 headed window can be cut off.
10. **Popup blocker**: the live-log window does not open; the run still works.
11. **Future Python**: invalid-escape `SyntaxWarning`s in the generator and generated scripts may become errors (**UNVERIFIED** in which version).

## 8. Most likely reasons it works on your Mac but fails on another Mac

1. **They installed with `pip install -r requirements.txt`**, which fails on the `python==3.12` line. Yours works because your venv was already there.
2. **Their `python3` is 3.13 or 3.14** (Homebrew's current default), and greenlet 3.0.3 cannot install. You use Homebrew **python@3.12** (`venv/pyvenv.cfg: home = /opt/homebrew/opt/python@3.12/bin`).
3. **They copied your folder with `venv/`**:
   - your venv points to `/opt/homebrew/...python3.12` and contains arm64-only Pillow, MarkupSafe and watchdog;
   - on an Intel Mac, or a Mac without that exact Homebrew Python, imports fail or the interpreter link is broken.
4. **They skipped `playwright install chromium`.** Your Chromium is in *your* `~/Library/Caches/ms-playwright`, which is not part of the project folder.
5. **They opened `http://localhost:5000`** and reached AirPlay Receiver instead of the app (**UNVERIFIED**). Fix: use `http://127.0.0.1:5000`, or turn off AirPlay Receiver in System Settings → General → AirDrop & Handoff.
6. **Their macOS is older than 13** (unofficial for Playwright 1.47), or **10.15 or older** (not installable).
7. **They followed the README**, which only gives Windows commands (`venv\Scripts\activate`) and does not mention macOS.

---

## 9. Ready-to-paste README section

```markdown
## Supported platforms

AutoFlow QA uses Playwright 1.47.0 with its bundled Chromium 129 (no Chrome/Edge needed).

| | Supported (minimum) | Recommended |
|---|---|---|
| Windows | Windows 10 64-bit (22H2) / Windows Server 2016+ | Windows 11 x64 |
| macOS | macOS 13 Ventura (Intel or Apple Silicon) | macOS 14 Sonoma or newer, Apple Silicon |
| Python | 3.9 (64-bit) | **3.12 (64-bit)** |
| RAM / disk | 8 GB / 1 GB free | 16 GB / 10 GB free (SSD) |

Not supported: Python 3.8 or older, Python 3.13 or newer (a pinned dependency, greenlet 3.0.3,
has no build for it), 32-bit Windows/Python, macOS 10.15 or older. Windows on ARM works only with
x64 Python under emulation (not officially supported).

Notes:
- Always create a fresh virtual environment on each machine - never copy `venv/` between computers.
- Run `python -m playwright install chromium` after installing the requirements.
- Open the app at http://127.0.0.1:5000 (on macOS, port 5000 is also used by AirPlay Receiver;
  `localhost` may reach AirPlay instead).
- Recording and Pick Element need a desktop session with a visible browser window.
```

**Before publishing it**, remove the `python==3.12` line from `requirements.txt`. That line is not a valid pip requirement. This report changed nothing.

## 10. New-machine compatibility checklist

Run these inside the project folder. Commands are given for **macOS** first, with Windows variants in brackets.

1. **OS version and architecture.**
   - macOS: `sw_vers` and `uname -m`. Expect 13+ and `arm64` or `x86_64`.
   - Windows: `winver`, or `systeminfo | findstr /B /C:"OS Name" /C:"OS Version" /C:"System Type"`. Expect Windows 10/11, x64-based.
2. **Python version.**
   - `python3 --version` [Windows: `py -3.12 --version`]. Expect **3.9-3.12, ideally 3.12**.
   - `python3 -c "import struct; print(struct.calcsize('P')*8)"`. Expect `64`.
3. **Create a fresh venv.**
   - `python3.12 -m venv venv` [Windows: `py -3.12 -m venv venv`].
4. **Install the requirements** (after removing the `python==3.12` line).
   - `venv/bin/pip install -r requirements.txt` [Windows: `venv\Scripts\pip install -r requirements.txt`].
5. **Download the browser.**
   - `venv/bin/python -m playwright install chromium`.
6. **Check versions.**
   - `venv/bin/python -m playwright --version`. Expect `Version 1.47.0`.
   - `venv/bin/pip show flask playwright pillow jinja2 watchdog greenlet | grep -E "Name|Version"` [Windows: `findstr` instead of `grep`].
7. **Check that all imports load.**
   - `venv/bin/python -c "import flask, playwright, PIL, jinja2, watchdog, greenlet; print('imports OK')"`.
8. **Check port 5000 is free.**
   - macOS: `lsof -nP -iTCP:5000 -sTCP:LISTEN`. Only `ControlCenter` (AirPlay) or nothing should appear.
   - Windows: `netstat -ano | findstr :5000`. Nothing should appear.
9. **Check disk space.**
   - macOS: `df -h .`. Windows: `dir`.
10. **Start the app** (`venv/bin/python app.py`) and open **http://127.0.0.1:5000**.
