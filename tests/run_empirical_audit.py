"""Empirical record -> replay -> diff harness for the Phase 1 audit.

Drives the REAL recorder/record_session.Recorder against a local fixture
page (tests/fixtures/page1.html + page2.html), using genuine Playwright-
synthesized (trusted) input events - not hand-crafted JSON - then feeds
the resulting recording straight through the REAL generator/
script_generator.generate_script() and runs the generated script exactly
the way executor/run_execution.py does. Nothing about the recorder or
generator is bypassed or mocked; only the human clicking through a
terminal-launched browser is replaced with scripted Playwright actions on
the same Recorder object app.py itself uses.

Usage: venv/Scripts/python.exe tests/run_empirical_audit.py
"""
import functools
import http.server
import json
import socketserver
import subprocess
import sys
import threading
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from playwright.sync_api import sync_playwright  # noqa: E402

from recorder.record_session import Recorder  # noqa: E402
from generator.script_generator import generate_script  # noqa: E402

FIXTURE_DIR = REPO_ROOT / "tests" / "fixtures"
PORT = 8899
BASE_URL = f"http://127.0.0.1:{PORT}/page1.html"


def start_server():
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(FIXTURE_DIR))
    httpd = socketserver.TCPServer(("127.0.0.1", PORT), handler)
    t = threading.Thread(target=httpd.serve_forever, daemon=True)
    t.start()
    return httpd


def record():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1280, "height": 800})
        page = context.new_page()
        page.goto(BASE_URL)

        recorder = Recorder(page)
        recorder.start()
        context.on("page", lambda new_page: recorder.record_new_tab(new_page))

        # 1. checkbox
        page.click("#agree-checkbox")
        # 2. radio
        page.click("#plan-pro")
        # 3. dropdown
        page.select_option("#country-select", "in")
        # 4. autofill-style input: value set directly (like a password
        # manager / browser autofill would), no synthetic input/change
        # event - only the blur-based fallback in action_capture.js
        # should catch this
        page.evaluate(
            "() => { const el = document.getElementById('email-field'); "
            "el.focus(); el.value = 'autofill@example.com'; }"
        )
        page.click("h1")  # blur email-field by clicking elsewhere
        # 5. inner scroll container (mouse must be over it for wheel to target it)
        page.hover("#scrollbox")
        page.mouse.wheel(0, 300)
        page.wait_for_timeout(400)  # > SCROLL_SETTLE_MS (250ms)
        # 6. window-level scroll (mouse over a plain area, not the scrollbox)
        page.hover("header")
        page.mouse.wheel(0, 500)
        page.wait_for_timeout(400)
        # 7. SPA route change via history.pushState
        page.click("#route-btn")
        page.wait_for_timeout(150)
        # 8. new tab
        with context.expect_page() as new_page_info:
            page.click("#newtab-link")
        new_page = new_page_info.value
        new_page.wait_for_load_state()
        page.wait_for_timeout(200)
        new_page.close()
        page.wait_for_timeout(200)
        # 9. footer link -> real cross-page navigation
        page.click("#footer-link")
        page.wait_for_load_state()
        page.wait_for_timeout(300)
        # 10. reload (evidence check: expect this to NOT appear in JSON)
        page.reload()
        page.wait_for_load_state()
        page.wait_for_timeout(300)
        # 11. back button (evidence check: expect a generic 'navigate', not a distinct type)
        page.go_back()
        page.wait_for_load_state()
        page.wait_for_timeout(500)

        test_case = recorder.stop(name="empirical_audit_fixture")
        browser.close()

    out_path = FIXTURE_DIR / "recorded_audit.json"
    out_path.write_text(json.dumps(test_case, indent=2), encoding="utf-8")
    print(f"\n=== RECORDED {len(test_case['actions'])} actions -> {out_path} ===")
    for i, a in enumerate(test_case["actions"]):
        print(f"[{i}] {a['action_type']:12s} value={a.get('value')!r:30s} url={a.get('page_url')}")
    return test_case


def replay(test_case):
    script_path = generate_script(test_case, out_name="empirical_audit_fixture", output_dir=FIXTURE_DIR)
    print(f"\n=== GENERATED SCRIPT: {script_path} ===")

    run_dir = FIXTURE_DIR / "audit_run"
    run_dir.mkdir(exist_ok=True)
    output_json = run_dir / "report.json"
    if output_json.exists():
        output_json.unlink()

    venv_python = REPO_ROOT / "venv" / "Scripts" / "python.exe"
    python_exe = str(venv_python) if venv_python.exists() else sys.executable
    cmd = [python_exe, str(script_path), BASE_URL, str(output_json), str(run_dir), "1", ""]
    print(f"\n=== RUNNING: {' '.join(cmd)} ===")
    proc = subprocess.run(cmd, cwd=str(REPO_ROOT), capture_output=True, text=True, timeout=180)
    print("--- stdout (tail) ---")
    print("\n".join(proc.stdout.splitlines()[-80:]))
    if proc.returncode != 0:
        print("--- stderr (tail) ---")
        print("\n".join(proc.stderr.splitlines()[-80:]))
    print(f"=== exit code: {proc.returncode} ===")

    if output_json.exists():
        report = json.loads(output_json.read_text(encoding="utf-8"))
        report_path = FIXTURE_DIR / "replay_report.json"
        report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(f"\n=== REPLAY REPORT saved -> {report_path} ===")
        return report
    else:
        print("\n=== NO report.json produced ===")
        return None


if __name__ == "__main__":
    httpd = start_server()
    try:
        tc = record()
        replay(tc)
    finally:
        httpd.shutdown()
