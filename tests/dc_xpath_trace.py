"""TEST-ONLY: same as dc_xpath_probe but traces every document.evaluate() XPath candidate tried during the click on
the input, by wrapping document.evaluate before action_capture.js's own init script runs."""
import sys
from pathlib import Path
BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))
from playwright.sync_api import sync_playwright
from recorder.record_session import Recorder

TRACE_JS = """
(function(){
  var orig = document.evaluate.bind(document);
  document.evaluate = function(expr, ...rest){
    console.log('[XPATH-TRY] ' + expr);
    return orig(expr, ...rest);
  };
})();
"""

with sync_playwright() as p:
    b = p.chromium.launch(headless=True)
    ctx = b.new_context()
    ctx.add_init_script(TRACE_JS)
    pg = ctx.new_page()
    pg.on("console", lambda m: print("[console]", m.text) if "[XPATH-TRY]" in m.text or "accName" in m.text else None)
    rec = Recorder(pg)
    rec.install_context_capture(ctx)
    pg.goto("https://the-internet.herokuapp.com/dynamic_controls", wait_until="domcontentloaded")
    pg.wait_for_timeout(800)
    rec.start(launch_url=pg.url)
    pg.click("#input-example button")
    pg.wait_for_timeout(3500)
    print("=== clicking input now ===")
    pg.click("#input-example input")
    pg.wait_for_timeout(300)
    tc = rec.stop(name="dc_xpath_trace", stop_reason="terminal_enter")
    drafts = (rec._draft_path, rec._draft_jsonl_path)
    b.close()
for d in drafts:
    if d: Path(d).unlink(missing_ok=True)
for i, a in enumerate(tc["actions"], 1):
    print(i, a["action_type"], (a.get("locator_profile") or {}).get("xpath"))
