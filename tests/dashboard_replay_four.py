"""TEST-ONLY: click Replay on each kept session's card in the real dashboard (server on 5001) and report the outcome."""
import time
from playwright.sync_api import sync_playwright
KEEP = ["session_20260928_170052_edited", "session_20260928_170352_edited",
        "session_20260928_171139_edited", "session_20260928_181934_edited"]
with sync_playwright() as p:
    b = p.chromium.launch(headless=True); pg = b.new_page()
    pg.goto("http://127.0.0.1:5001/"); pg.wait_for_selector(".recording-card")
    for name in KEEP:
        card = pg.locator(".recording-card").filter(has=pg.locator(f"h3:text-is('{name}')")).first
        btn = card.locator("button", has_text="Replay")
        t0 = time.time(); btn.click()
        pg.wait_for_timeout(1500)
        pg.wait_for_function("(el) => !el.disabled", arg=btn.element_handle(), timeout=540000)
        txt = card.locator(".editor-message, .editor-error, .validation-panel").first.inner_text().replace("\n", " | ")[:170]
        print(f"REPLAY {name}: {time.time()-t0:.0f}s -> {txt}", flush=True)
    b.close()
