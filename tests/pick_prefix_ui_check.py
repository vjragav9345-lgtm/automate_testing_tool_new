"""TEST-ONLY: the four Pick Element checks through the REAL editor UI. The real Flask app runs inside this process
(port 5001) so the picker thread's own test-drive queue can report which pages exist / which one carries the overlay."""
import json, sys, threading, time
from pathlib import Path
BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))
import app as appmod
import recorder.pick_element as pe
from werkzeug.serving import make_server
from playwright.sync_api import sync_playwright

class _Tee:
    def __init__(self, real): self.real, self.lines = real, []
    def write(self, t):
        self.lines.append(t); return self.real.write(t)
    def flush(self): return self.real.flush()
    def __getattr__(self, n): return getattr(self.real, n)
_tee = _Tee(sys.stdout); sys.stdout = _tee
import re

srv = make_server("127.0.0.1", 5001, appmod.app, threaded=True)
threading.Thread(target=srv.serve_forever, daemon=True).start()

def run_case(pw_page, label, path, mode, step_no, expect):
    """mode 'after' | 'before' on step_no (1-based). Returns picker-thread report."""
    out = {}
    def drive(browser, context):
        info = []
        for p in context.pages:
            try:
                info.append({"url": p.url, "picker_overlay": bool(p.evaluate("!!window.__afqaPickMode")), "front_tab": p.evaluate("document.visibilityState") == "visible"})
            except Exception as e:
                info.append({"url": p.url, "picker_overlay": f"err {e}"[:50]})
        out["pages"] = info
        out["url_checks"] = [v.get("page_url_check") for v in list(pe._PICK_RESULTS.values()) if v.get("page_url_check")]
        browser.close()
    pw_page.goto(f"http://127.0.0.1:5001/recording/edit?path={path}")
    pw_page.wait_for_selector("#actionsList > *", timeout=20000)
    title_sel = 'button[title="Add Action After"]' if mode == "after" else 'button[title="Add Action Before"]'
    pw_page.locator(title_sel).nth(step_no - 1).click()
    title = pw_page.locator("#modalTitle").inner_text()
    ctx = pw_page.evaluate("({mode: modalContext.mode, index: modalContext.index, insertAfterIndex: modalContext.insertAfterIndex, pageId: modalContext.pageId})")
    pw_page.click("#modalPickElementBtn")
    pe._TEST_DRIVE_QUEUE.put(drive)
    t0 = time.time()
    while "pages" not in out and time.time() - t0 < 240:
        time.sleep(0.5)
    time.sleep(1.0)
    pw_page.click("#modalCancelBtn")
    print(f"\n===== {label}\n  modal title: {title!r}\n  modalContext: {ctx}\n  picker thread pages: {json.dumps(out.get('pages'))}", flush=True)
    uc = (out.get("url_checks") or [None])[-1] or {}
    landed = uc.get("actual_url")
    proof = f"picker status page_url_check={uc}"
    front = [p["url"] for p in (out.get("pages") or []) if p["front_tab"] is True]
    print(f"  proof log: {proof[:330]}", flush=True)
    print(f"  picker landing page: {landed}", flush=True)
    print(f"  tab in front (visible): {front}", flush=True)
    ok = expect(landed) and (not front or landed in front)
    print(f"  expectation {'MET' if ok else 'NOT MET'}", flush=True)
    assert ok, label
    return out

with sync_playwright() as p:
    b = p.chromium.launch(headless=True); pg = b.new_page()
    pg.on("dialog", lambda d: d.accept())
    R = "storage/recordings/session_20260928_224136.json"
    run_case(pg, "CHECK 1: Myntra, Add Action After Step 4 (product tile click that opens the product in a new tab)", R, "after", 4,
             lambda u: "/buy" in u and "levis" in u.lower())
    run_case(pg, "CHECK 2: Myntra, Add Action After Step 2 (right after clicking T-Shirts)", R, "after", 2,
             lambda u: u.rstrip("/").endswith("/men-tshirts"))
    run_case(pg, "CHECK 3: Myntra, first action (Add Action Before Step 1 - no steps precede it)", R, "before", 1,
             lambda u: u.rstrip("/") == "https://www.myntra.com")
    run_case(pg, "CHECK 4: different site (Blinkit), Add Action After Step 5", "storage/recordings/edited/session_20260928_171139_edited.json", "after", 5,
             lambda u: "blinkit.com" in u)
    b.close()
print("\nALL FOUR PICK CHECKS PASSED")
import os; os._exit(0)
