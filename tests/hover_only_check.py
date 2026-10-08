"""TEST-ONLY: the recorder still saves a Hover step when the user ONLY hovers a trigger (no click) and then
clicks an item inside the menu; record with the real Recorder, then replay."""
import importlib.util, sys
from pathlib import Path
BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE)); sys.path.insert(0, str(Path(__file__).resolve().parent))
from playwright.sync_api import sync_playwright
from phase4_fixture_server import FixtureServer
from recorder.record_session import Recorder
from storage import repository
from generator.script_generator import generate_script
OUT = BASE / "tests/_probe_out/hover_only"; OUT.mkdir(parents=True, exist_ok=True)
def center(pg, sel):
    bb = pg.locator(sel).first.bounding_box(); return bb["x"] + bb["width"] / 2, bb["y"] + bb["height"] / 2
fails = []
with FixtureServer() as fx:
    url = fx.url("rv_mega_hover.html")
    for style in ("direct", "dwell", "via-panel", "off-screen-menu"):
        if style == "off-screen-menu":
            url = fx.url("g_hover_offscreen.html")
        with sync_playwright() as p:
            b = p.chromium.launch(headless=True); ctx = b.new_context(viewport={"width": 1100, "height": 700}); pg = ctx.new_page()
            rec = Recorder(pg); rec.install_context_capture(ctx); pg.goto(url); pg.wait_for_timeout(300); rec.start(launch_url=url)
            trig = "#top" if style == "off-screen-menu" else "#feat"
            x, y = center(pg, trig); pg.mouse.move(x, y, steps=8)                      # hover ONLY - no click on the trigger
            pg.wait_for_timeout(900 if style == "dwell" else 250)
            if style == "via-panel":
                a, c = center(pg, "aside.panel"); pg.mouse.move(a, c, steps=10); pg.wait_for_timeout(300)
            a, c = center(pg, "#s1" if style == "off-screen-menu" else "#pa"); pg.mouse.move(a, c, steps=10); pg.wait_for_timeout(200); pg.mouse.click(a, c)
            pg.wait_for_timeout(2500)
            tc = rec.stop(name=f"hov_{style}", stop_reason="terminal_enter")
            for d in (rec._draft_path, rec._draft_jsonl_path):
                if d: Path(d).unlink(missing_ok=True)
            b.close()
        tc = repository.migrate_recording(tc)
        kinds = [(a["action_type"], ((a.get("locator_profile") or {}).get("text") or "")[:13]) for a in tc["actions"]]
        print(style, kinds)
        want = [("navigate", ""), ("hover", "Products"), ("click", "Analytics tool")] if style == "off-screen-menu" else [("navigate", ""), ("hover", "Features"), ("click", "Pro Analytics")]
        if len(kinds) != len(want) or any(k != w[0] or not n.startswith(w[1][:13]) for (k, n), w in zip(kinds, want)):
            fails.append((style, kinds))
        d = OUT / style; d.mkdir(exist_ok=True)
        sp = generate_script(tc, out_name=f"{style}.py", output_dir=d)
        spec = importlib.util.spec_from_file_location(style, sp); m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
        res = m.run(url, output_json_path=d / "report.json", screenshot_dir=d / "shots", headless=True)
        ok = all(s["success"] for s in res["steps"]) and ("g_next" if style == "off-screen-menu" else "hov_menu_target") in (res.get("final_url") or "")
        print("  replay:", "PASS" if ok else "FAIL", [s["success"] for s in res["steps"]], res.get("final_url"))
        if not ok: fails.append((style, "replay"))
print("HOVER ONLY CHECK", "PASS" if not fails else f"FAIL {fails}")
sys.exit(1 if fails else 0)
