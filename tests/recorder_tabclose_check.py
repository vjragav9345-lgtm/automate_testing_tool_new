"""TEST-ONLY: Phase A verification for the recorder-side _on_page_closed fix.
Case 1: a single-page session whose only close is the browser/last page closing (simulating
"closed the browser to stop recording") -> must NOT record a tab_close action.
Case 2: a two-page session where the user closes the SECOND (non-last) page while the first
remains open (a genuine mid-test tab close) -> MUST still record a real tab_close action."""
import sys
import time
from pathlib import Path
BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))
from playwright.sync_api import sync_playwright
from recorder.record_session import Recorder

URL = "https://the-internet.herokuapp.com/windows"

# Case 1: closing the only/last page must NOT record a tab_close
with sync_playwright() as p:
    b = p.chromium.launch(headless=True)
    ctx = b.new_context()
    pg = ctx.new_page()
    rec = Recorder(pg)
    rec.install_context_capture(ctx)
    pg.goto(URL, wait_until="domcontentloaded")
    pg.wait_for_timeout(300)
    rec.start(launch_url=pg.url)
    pg.close()  # simulates "closed the browser to stop recording" - the ONLY page closing
    time.sleep(0.3)
    action_types = [a["action_type"] for a in rec.actions]
    print("Case 1 (last page closed) recorded action_types:", action_types)
    assert "tab_close" not in action_types, "a spurious tab_close must NOT be recorded when the last page closes"
    print("PASS: no spurious tab_close recorded for the last-page-closing case")
    try:
        b.close()
    except Exception:
        pass

# Case 2: closing a SECOND page while the first remains open must record a real tab_close
with sync_playwright() as p:
    b = p.chromium.launch(headless=True)
    ctx = b.new_context()
    pg = ctx.new_page()
    rec = Recorder(pg)
    rec.install_context_capture(ctx)
    pg.goto(URL, wait_until="domcontentloaded")
    pg.wait_for_timeout(300)
    rec.start(launch_url=pg.url)
    with ctx.expect_page() as new_page_info:
        pg.click("text=Click Here")
    new_page = new_page_info.value
    new_page.wait_for_load_state("domcontentloaded")
    rec.record_new_tab(new_page)
    pg.wait_for_timeout(300)
    new_page.close()  # a genuine mid-test tab close - page 0 remains open
    pg.wait_for_timeout(300)
    action_types = [a["action_type"] for a in rec.actions]
    print("Case 2 (second page closed, first remains open) recorded action_types:", action_types)
    assert "tab_close" in action_types, "a genuine mid-test tab_close on a non-last page MUST still be recorded"
    print("PASS: a genuine mid-test tab_close is still recorded correctly")
    b.close()
