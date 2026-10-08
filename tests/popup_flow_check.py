"""TEST-ONLY: ISSUE 1 - replay never closes a popup/dropdown a previous recorded step opened.
Records (real Recorder): click opener -> click the popup's icon-only X -> open dropdown -> click item.
Replays: the X is clicked by the recorded step (exactly once), nothing else closed anything."""
import importlib.util, sys, time
from pathlib import Path
BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE)); sys.path.insert(0, str(Path(__file__).resolve().parent))
from playwright.sync_api import sync_playwright
from phase4_fixture_server import FixtureServer
from recorder.record_session import Recorder
from storage import repository
from generator.script_generator import generate_script
OUT = BASE / "tests/_probe_out/popup_flow"; OUT.mkdir(parents=True, exist_ok=True)

def center(pg, sel):
    bb = pg.locator(sel).first.bounding_box(); return bb["x"] + bb["width"] / 2, bb["y"] + bb["height"] / 2
def mv(pg, sel, click=True):
    x, y = center(pg, sel); pg.mouse.move(x, y, steps=8); pg.wait_for_timeout(250)
    if click: pg.mouse.click(x, y); pg.wait_for_timeout(500)

with FixtureServer() as fx:
    url = fx.url("pop_flow.html")
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True); ctx = b.new_context(viewport={"width": 1000, "height": 600}); pg = ctx.new_page()
        rec = Recorder(pg); rec.install_context_capture(ctx); pg.goto(url); rec.start(launch_url=url)
        mv(pg, "#watch"); mv(pg, "#xbtn"); mv(pg, "#lang"); mv(pg, "#es")
        pg.wait_for_timeout(2500)
        tc = rec.stop(name="popup_flow", stop_reason="terminal_enter")
        for d in (rec._draft_path, rec._draft_jsonl_path):
            if d: Path(d).unlink(missing_ok=True)
        b.close()
    print("recorded:", [(a["action_type"], ((a.get("locator_profile") or {}).get("title") or (a.get("locator_profile") or {}).get("text") or "")[:12]) for a in tc["actions"]])
    tc = repository.migrate_recording(tc)
    sp = generate_script(tc, out_name="popup_flow.py", output_dir=OUT)
    spec = importlib.util.spec_from_file_location("popup_flow", sp); m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    # count the X clicks the page really received
    res = m.run(url, output_json_path=OUT / "report.json", screenshot_dir=OUT / "shots", headless=True)
    for s in res["steps"]:
        print(" ", s["index"], s["action_type"], "ok=" + str(s["success"]), "|", (s.get("error") or s.get("warning") or "")[:140])
    log = [e["message"] for e in (res.get("live_log") or [])]
    print("  sub-lines:", log)
    fails = []
    if not all(s["success"] for s in res["steps"]): fails.append("not all steps pass")
    if any(s.get("warning") and "already closed" in s["warning"] for s in res["steps"]): fails.append("'already closed' warning: the popup was closed by something else")
    if any("already closed" in l for l in log): fails.append("popup reported 'already closed' (something closed it before the recorded X click)")
    if any("unexpected popup" in l or "covering the target" in l or "covering the page" in l for l in log): fails.append("an auto-dismiss helper ran")
    if "hov_menu_target" not in (res.get("final_url") or ""): fails.append(f"wrong final url {res.get('final_url')}")
    print("POPUP FLOW", "PASS" if not fails else f"FAIL {fails}")
    sys.exit(1 if fails else 0)
