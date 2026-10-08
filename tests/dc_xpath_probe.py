"""TEST-ONLY: record a real click on the dynamic_controls input (after Enable) via the REAL recorder,
and print exactly what locator_profile.xpath (and xpath_candidates, if any) got captured."""
import json, sys
from pathlib import Path
BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))
from playwright.sync_api import sync_playwright
from recorder.record_session import Recorder

with sync_playwright() as p:
    b = p.chromium.launch(headless=True)
    ctx = b.new_context()
    pg = ctx.new_page()
    rec = Recorder(pg)
    rec.install_context_capture(ctx)
    pg.goto("https://the-internet.herokuapp.com/dynamic_controls", wait_until="domcontentloaded")
    pg.wait_for_timeout(800)
    rec.start(launch_url=pg.url)
    pg.click("#input-example button")
    pg.wait_for_timeout(3500)
    print("input disabled after Enable+wait?", pg.locator("#input-example input").is_disabled())
    pg.click("#input-example input")
    pg.wait_for_timeout(300)
    tc = rec.stop(name="dc_xpath_probe", stop_reason="terminal_enter")
    drafts = (rec._draft_path, rec._draft_jsonl_path)
    b.close()
for d in drafts:
    if d: Path(d).unlink(missing_ok=True)
for i, a in enumerate(tc["actions"], 1):
    print(i, a["action_type"], json.dumps((a.get("locator_profile") or {}).get("xpath"), ensure_ascii=False))
