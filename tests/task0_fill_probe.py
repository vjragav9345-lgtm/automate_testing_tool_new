"""TEST-ONLY: drives the REAL Recorder (headless) on tests/fixtures/task0_fill_fixture.html for each 'typed value, no Enter'
scenario and prints what the saved recording contains (type / value / order). Not saved into storage/recordings."""
import sys
from pathlib import Path
BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE)); sys.path.insert(0, str(Path(__file__).resolve().parent))
from playwright.sync_api import sync_playwright
from recorder.record_session import Recorder
from phase4_fixture_server import FixtureServer

def run(srv, name, steps):
    url = srv.url("task0_fill_fixture.html")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(viewport={"width": 1000, "height": 600})
        page = ctx.new_page()
        rec = Recorder(page); rec.install_context_capture(ctx)
        page.goto(url, wait_until="domcontentloaded"); page.wait_for_timeout(800)
        rec.start(launch_url=url)
        logs = []
        page.on("console", lambda m: logs.append(m.text) if "[FILL-FLUSH]" in m.text else None)
        steps(page, ctx, rec)
        import time; time.sleep(1.2)
        tc = rec.stop(name=name, stop_reason="terminal_enter")
        drafts = (rec._draft_path, rec._draft_jsonl_path)
        browser.close()
    for d in drafts:
        if d: Path(d).unlink(missing_ok=True)
    acts = [(a["action_type"], a.get("value"), (a.get("locator_profile") or {}).get("id") or (a.get("locator_profile") or {}).get("text"), (a.get("page_url") or "").rsplit("/", 1)[-1]) for a in tc["actions"]]
    print(f"\n=== {name}\n  saved actions: {acts}\n  flush logs: {logs}")
    return tc

def type_q(page, text="laptop"):
    page.click("#q"); page.keyboard.type(text, delay=60)

SCEN = {
 "A_blur_click_elsewhere": lambda pg, c, r: (type_q(pg), pg.click("#elsewhere")),
 "B_click_suggestion_keeps_focus": lambda pg, c, r: (type_q(pg), pg.click("#sug1"), pg.wait_for_timeout(800)),
 "C_navigate_away_by_url": lambda pg, c, r: (type_q(pg), pg.goto(pg.url.rsplit("/", 1)[0] + "/task0_fill_page2.html"), pg.wait_for_timeout(800)),
 "D_close_tab_while_focused": lambda pg, c, r: (type_q(pg), pg.close(run_before_unload=True)),
 "E_stop_recording_focused": lambda pg, c, r: (type_q(pg),),
 "F_enter_control": lambda pg, c, r: (type_q(pg), pg.keyboard.press("Enter"), pg.click("#elsewhere")),
 "H_other_action_escape_key": lambda pg, c, r: (type_q(pg), pg.keyboard.press("Escape")),
 "G_click_no_typing": lambda pg, c, r: (pg.click("#q"), pg.click("#elsewhere")),
}
if __name__ == "__main__":
    which = sys.argv[1:] or list(SCEN)
    with FixtureServer() as srv:
        for n in which:
            run(srv, "task0_" + n, SCEN[n])
